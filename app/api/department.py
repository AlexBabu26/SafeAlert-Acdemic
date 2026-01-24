"""
Department API endpoints (formerly Dispatcher)
Handles incident management, respondent management, and department operations
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from datetime import datetime, timedelta
from sqlalchemy import func, or_, case

from app.extensions import db
from app.models import (
    User, 
    IncidentReport, 
    IncidentAssignment, 
    AssignmentStatus,
    IncidentStatus,
    Department,
    DepartmentType,
    SafetyAlert,
    StatusHistory,
)
from app.schemas.incident import IncidentReportSchema, IncidentListSchema, IncidentStatusUpdateSchema
from app.schemas.assignment import IncidentAssignmentSchema, AssignmentListSchema
from app.schemas.department import DepartmentSchema, DepartmentListSchema, DepartmentCreateSchema
from app.schemas.alert import SafetyAlertSchema, SafetyAlertCreateSchema
from app.schemas.user import UserAdminSchema
from app.utils.permissions import department_required, department_or_admin_required
from app.services.allocation import AllocationService, get_nearby_departments
from app.services.escalation import EscalationService
from app.services.notification import NotificationService
from app.services.department_analytics import (
    get_department_summary_stats,
    get_department_timeseries_data
)
from app.socketio_events import broadcast_incident_updated, broadcast_assignment_created, broadcast_safety_alert

bp = Blueprint('department', __name__)


# ==================== Incident Management ====================

@bp.route('/incidents/', methods=['GET'])
@department_required
def list_incidents(user):
    """List all active incidents for department view"""
    # Filter parameters
    status = request.args.get('status')
    severity = request.args.get('severity')
    category_id = request.args.get('category', type=int)
    search = request.args.get('search')
    
    # Base query - all incidents
    query = IncidentReport.query
    
    # Apply filters
    if status:
        query = query.filter(IncidentReport.status == status)
    else:
        # Default: show active incidents
        query = query.filter(IncidentReport.status.in_(IncidentStatus.ACTIVE_STATUSES))
    
    if severity:
        query = query.filter(IncidentReport.severity == severity)
    
    if category_id:
        query = query.filter(IncidentReport.category_id == category_id)
    
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            or_(
                IncidentReport.title.ilike(search_pattern),
                IncidentReport.description.ilike(search_pattern),
                IncidentReport.location_text.ilike(search_pattern)
            )
        )
    
    # Order by severity (critical first) and time
    # Use CASE WHEN for SQLite compatibility (instead of MySQL's FIELD function)
    severity_order = case(
        (IncidentReport.severity == 'CRITICAL', 1),
        (IncidentReport.severity == 'HIGH', 2),
        (IncidentReport.severity == 'MEDIUM', 3),
        (IncidentReport.severity == 'LOW', 4),
        (IncidentReport.severity == 'INFO', 5),
        else_=6
    )
    query = query.order_by(
        severity_order,
        IncidentReport.created_at.desc()
    )
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('PAGINATION_PER_PAGE', 20)
    
    total = query.count()
    incidents = query.offset((page - 1) * per_page).limit(per_page).all()
    
    schema = IncidentListSchema(many=True)
    
    return jsonify({
        'count': total,
        'next': f'/api/department/incidents/?page={page + 1}' if page * per_page < total else None,
        'previous': f'/api/department/incidents/?page={page - 1}' if page > 1 else None,
        'results': schema.dump(incidents)
    }), 200


@bp.route('/incidents/<int:id>/', methods=['GET'])
@department_required
def get_incident(user, id):
    """Get incident details for department"""
    incident = IncidentReport.query.get(id)
    
    if not incident:
        return jsonify({'detail': 'Not found.'}), 404
    
    schema = IncidentReportSchema()
    result = schema.dump(incident)
    
    # Include assignments
    assignment_schema = IncidentAssignmentSchema(many=True)
    result['assignments'] = assignment_schema.dump(incident.assignments.all())
    
    return jsonify(result), 200


@bp.route('/incidents/<int:id>/assign/', methods=['POST'])
@department_required
def assign_incident(user, id):
    """Manually assign incident to departments"""
    incident = IncidentReport.query.get(id)
    
    if not incident:
        return jsonify({'detail': 'Not found.'}), 404
    
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    department_ids = request.json.get('department_ids', [])
    auto_allocate = request.json.get('auto_allocate', False)
    
    if auto_allocate:
        # Use smart allocation
        allocation_service = AllocationService()
        assignments = allocation_service.allocate_incident(incident)
        
        # Notify responders
        notification_service = NotificationService()
        for assignment in assignments:
            notification_service.notify_assignment_created(assignment)
            broadcast_assignment_created(assignment)
        
        schema = IncidentAssignmentSchema(many=True)
        return jsonify({
            'message': f'Allocated to {len(assignments)} department(s)',
            'assignments': schema.dump(assignments)
        }), 201
    
    elif department_ids:
        # Manual assignment
        assignments = []
        allocation_service = AllocationService()
        
        for dept_id in department_ids:
            assignment = allocation_service.add_department_to_incident(incident, dept_id)
            if assignment:
                assignments.append(assignment)
        
        # Update incident status if not already dispatched
        if incident.status in ['REPORTED', 'VERIFIED']:
            incident.dispatch()
            db.session.commit()
        
        # Notify responders
        notification_service = NotificationService()
        for assignment in assignments:
            notification_service.notify_assignment_created(assignment)
            broadcast_assignment_created(assignment)
        
        broadcast_incident_updated(incident)
        
        schema = IncidentAssignmentSchema(many=True)
        return jsonify({
            'message': f'Assigned to {len(assignments)} department(s)',
            'assignments': schema.dump(assignments)
        }), 201
    
    return jsonify({'detail': 'Either department_ids or auto_allocate required.'}), 400


@bp.route('/incidents/<int:id>/status/', methods=['PATCH'])
@department_required
def update_incident_status(user, id):
    """Update incident status"""
    incident = IncidentReport.query.get(id)
    
    if not incident:
        return jsonify({'detail': 'Not found.'}), 404
    
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    schema = IncidentStatusUpdateSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    old_status = incident.status
    new_status = data['status']
    notes = data.get('notes', '')
    
    # Update status
    incident.status = new_status
    
    # Create status history
    history = StatusHistory(
        incident_id=incident.id,
        old_status=old_status,
        new_status=new_status,
        changed_by_id=user.id,
        notes=notes,
        source='DEPARTMENT'
    )
    db.session.add(history)
    
    # If verified, trigger auto-allocation
    if new_status == 'VERIFIED' and old_status == 'REPORTED':
        allocation_service = AllocationService()
        assignments = allocation_service.allocate_incident(incident)
        
        # Notify responders
        notification_service = NotificationService()
        for assignment in assignments:
            notification_service.notify_assignment_created(assignment)
            broadcast_assignment_created(assignment)
    
    db.session.commit()
    
    # Broadcast update
    broadcast_incident_updated(incident)
    
    # Notify status change
    notification_service = NotificationService()
    notification_service.notify_status_change(incident, old_status, new_status)
    
    response_schema = IncidentReportSchema()
    return jsonify(response_schema.dump(incident)), 200


@bp.route('/incidents/<int:id>/escalate/', methods=['POST'])
@department_required
def escalate_incident(user, id):
    """Manually escalate an incident"""
    incident = IncidentReport.query.get(id)
    
    if not incident:
        return jsonify({'detail': 'Not found.'}), 404
    
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    action_type = request.json.get('action_type', 'ADD_DEPARTMENT')
    reason = request.json.get('reason')
    
    escalation_service = EscalationService()
    log = escalation_service.manual_escalate(incident, action_type, user, reason)
    
    return jsonify({
        'message': 'Escalation executed',
        'action_type': log.action_type,
        'result': log.action_result,
        'is_successful': log.is_successful,
    }), 200


@bp.route('/incidents/<int:id>/nearby-departments/', methods=['GET'])
@department_required
def get_nearby_departments_for_incident(user, id):
    """Get top 5 nearby departments for an incident with distance and priority"""
    incident = IncidentReport.query.get(id)
    
    if not incident:
        return jsonify({'detail': 'Not found.'}), 404
    
    if not incident.latitude or not incident.longitude:
        return jsonify({'detail': 'Incident has no location data.'}), 400
    
    # Get nearby departments sorted by distance
    radius_km = request.args.get('radius', 50.0, type=float)
    limit = request.args.get('limit', 5, type=int)
    
    nearby = get_nearby_departments(
        float(incident.latitude),
        float(incident.longitude),
        radius_km=radius_km
    )
    
    # Get existing assignments for this incident
    existing_assignments = {
        a.department_id: a for a in incident.assignments.all()
    }
    
    results = []
    for idx, (dept, distance_km) in enumerate(nearby[:limit]):
        assignment = existing_assignments.get(dept.id)
        
        # Calculate a priority score (lower is better)
        # Based on: distance, capacity, response time
        priority_score = (
            distance_km * 10 +  # Distance factor
            (dept.current_active_incidents / max(dept.max_concurrent_incidents, 1)) * 50 +  # Load factor
            (dept.average_response_time_minutes or 30)  # Response time factor
        )
        
        results.append({
            'id': dept.id,
            'name': dept.name,
            'code': dept.code,
            'type': dept.type,
            'distance_km': round(distance_km, 2),
            'priority_rank': idx + 1,
            'priority_score': round(priority_score, 1),
            'headquarters_lat': float(dept.headquarters_lat),
            'headquarters_lng': float(dept.headquarters_lng),
            'contact_phone': dept.contact_phone,
            'current_active_incidents': dept.current_active_incidents,
            'max_concurrent_incidents': dept.max_concurrent_incidents,
            'available_capacity': dept.available_capacity,
            'average_response_time': dept.average_response_time_minutes,
            'is_assigned': assignment is not None,
            'assignment_status': assignment.status if assignment else None,
            'assignment_priority': assignment.priority_rank if assignment else None,
        })
    
    return jsonify({
        'incident_id': incident.id,
        'incident_location': {
            'latitude': float(incident.latitude),
            'longitude': float(incident.longitude),
            'text': incident.location_text
        },
        'departments': results,
        'total_found': len(nearby)
    }), 200


# ==================== Respondent Management ====================

@bp.route('/respondents/', methods=['GET'])
@department_required
def list_respondents(user):
    """List all respondents under this department"""
    # Only show respondents from the department user's department
    query = User.query.filter(
        User.department_id == user.department_id,
        User.is_responder == True
    )
    
    # Optional filters
    is_active = request.args.get('is_active')
    is_on_duty = request.args.get('is_on_duty')
    is_available = request.args.get('is_available')
    search = request.args.get('search')
    
    if is_active is not None:
        is_active_bool = is_active.lower() in ('true', '1', 'yes')
        query = query.filter(User.is_active == is_active_bool)
    
    if is_on_duty is not None:
        is_on_duty_bool = is_on_duty.lower() in ('true', '1', 'yes')
        query = query.filter(User.is_on_duty == is_on_duty_bool)
    
    if is_available is not None:
        is_available_bool = is_available.lower() in ('true', '1', 'yes')
        query = query.filter(User.is_available == is_available_bool)
    
    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            or_(
                User.username.ilike(search_filter),
                User.first_name.ilike(search_filter),
                User.last_name.ilike(search_filter),
                User.badge_number.ilike(search_filter)
            )
        )
    
    respondents = query.order_by(User.username).all()
    
    schema = UserAdminSchema(many=True)
    return jsonify({
        'results': schema.dump(respondents),
        'total': len(respondents)
    }), 200


@bp.route('/respondents/pending/', methods=['GET'])
@department_required
def list_pending_respondents(user):
    """List respondents pending activation under this department"""
    respondents = User.query.filter(
        User.department_id == user.department_id,
        User.is_responder == True,
        User.is_active == False
    ).order_by(User.date_joined.desc()).all()
    
    schema = UserAdminSchema(many=True)
    return jsonify({
        'results': schema.dump(respondents),
        'total': len(respondents)
    }), 200


@bp.route('/respondents/<int:respondent_id>/', methods=['GET'])
@department_required
def get_respondent(user, respondent_id):
    """Get respondent details"""
    respondent = User.query.get(respondent_id)
    
    if not respondent:
        return jsonify({'detail': 'Respondent not found.'}), 404
    
    # Ensure respondent belongs to the same department
    if respondent.department_id != user.department_id:
        return jsonify({'detail': 'You can only view respondents from your department.'}), 403
    
    if not respondent.is_responder:
        return jsonify({'detail': 'User is not a respondent.'}), 400
    
    schema = UserAdminSchema()
    result = schema.dump(respondent)
    
    # Add assignment stats
    today = datetime.utcnow().date()
    active_assignments = IncidentAssignment.query.filter(
        IncidentAssignment.responder_id == respondent.id,
        IncidentAssignment.status.in_(AssignmentStatus.ACTIVE_STATUSES)
    ).count()
    
    completed_today = IncidentAssignment.query.filter(
        IncidentAssignment.responder_id == respondent.id,
        IncidentAssignment.status == AssignmentStatus.COMPLETED,
        func.date(IncidentAssignment.completed_at) == today
    ).count()
    
    result['stats'] = {
        'active_assignments': active_assignments,
        'completed_today': completed_today,
    }
    
    return jsonify(result), 200


@bp.route('/respondents/<int:respondent_id>/activate/', methods=['POST'])
@department_required
def activate_respondent(user, respondent_id):
    """Activate a respondent account under this department"""
    respondent = User.query.get(respondent_id)
    
    if not respondent:
        return jsonify({'detail': 'Respondent not found.'}), 404
    
    # Ensure respondent belongs to the same department
    if respondent.department_id != user.department_id:
        return jsonify({'detail': 'You can only manage respondents from your department.'}), 403
    
    if not respondent.is_responder:
        return jsonify({'detail': 'User is not a respondent.'}), 400
    
    if respondent.is_active:
        return jsonify({'detail': 'Respondent is already active.'}), 400
    
    respondent.is_active = True
    db.session.commit()
    
    schema = UserAdminSchema()
    return jsonify({
        'message': f'Respondent {respondent.username} has been activated.',
        'user': schema.dump(respondent)
    }), 200


@bp.route('/respondents/<int:respondent_id>/deactivate/', methods=['POST'])
@department_required
def deactivate_respondent(user, respondent_id):
    """Deactivate a respondent account under this department"""
    respondent = User.query.get(respondent_id)
    
    if not respondent:
        return jsonify({'detail': 'Respondent not found.'}), 404
    
    # Ensure respondent belongs to the same department
    if respondent.department_id != user.department_id:
        return jsonify({'detail': 'You can only manage respondents from your department.'}), 403
    
    if not respondent.is_responder:
        return jsonify({'detail': 'User is not a respondent.'}), 400
    
    if not respondent.is_active:
        return jsonify({'detail': 'Respondent is already deactivated.'}), 400
    
    respondent.is_active = False
    respondent.is_on_duty = False
    respondent.is_available = False
    db.session.commit()
    
    schema = UserAdminSchema()
    return jsonify({
        'message': f'Respondent {respondent.username} has been deactivated.',
        'user': schema.dump(respondent)
    }), 200


@bp.route('/assignments/<int:assignment_id>/assign-respondent/', methods=['POST'])
@department_required
def assign_respondent_to_task(user, assignment_id):
    """Assign a specific respondent to an assignment/task"""
    assignment = IncidentAssignment.query.get(assignment_id)
    
    if not assignment:
        return jsonify({'detail': 'Assignment not found.'}), 404
    
    # Ensure assignment belongs to the same department
    if assignment.department_id != user.department_id:
        return jsonify({'detail': 'You can only manage assignments from your department.'}), 403
    
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    respondent_id = request.json.get('respondent_id')
    if not respondent_id:
        return jsonify({'detail': 'respondent_id is required.'}), 400
    
    respondent = User.query.get(respondent_id)
    
    if not respondent:
        return jsonify({'detail': 'Respondent not found.'}), 404
    
    # Validate respondent
    if respondent.department_id != user.department_id:
        return jsonify({'detail': 'Respondent must be from your department.'}), 403
    
    if not respondent.is_responder:
        return jsonify({'detail': 'User is not a respondent.'}), 400
    
    if not respondent.is_active:
        return jsonify({'detail': 'Respondent account is not active.'}), 400
    
    # Assign the respondent
    assignment.responder_id = respondent_id
    db.session.commit()
    
    # Notify the respondent
    notification_service = NotificationService()
    notification_service.notify_assignment_created(assignment)
    
    schema = IncidentAssignmentSchema()
    return jsonify({
        'message': f'Assignment assigned to {respondent.full_name}.',
        'assignment': schema.dump(assignment)
    }), 200


# ==================== Map & Real-time Data ====================

@bp.route('/map/', methods=['GET'])
@department_required
def get_map_data(user):
    """Get real-time map data for department command center"""
    # Get all active incidents with location
    active_incidents = IncidentReport.query.filter(
        IncidentReport.status.in_(IncidentStatus.ACTIVE_STATUSES),
        IncidentReport.latitude.isnot(None),
        IncidentReport.longitude.isnot(None)
    ).all()
    
    # Get all on-duty responders with location
    on_duty_responders = User.query.filter(
        User.is_responder == True,
        User.is_on_duty == True,
        User.current_latitude.isnot(None),
        User.current_longitude.isnot(None)
    ).all()
    
    # Get all departments
    departments = Department.query.filter(Department.is_active == True).all()
    
    return jsonify({
        'incidents': [{
            'id': inc.id,
            'title': inc.title,
            'severity': inc.severity,
            'status': inc.status,
            'category': inc.category.name if inc.category else None,
            'latitude': float(inc.latitude),
            'longitude': float(inc.longitude),
            'created_at': inc.created_at.isoformat(),
        } for inc in active_incidents],
        'responders': [{
            'id': resp.id,
            'name': resp.full_name,
            'department_id': resp.department_id,
            'latitude': float(resp.current_latitude),
            'longitude': float(resp.current_longitude),
            'is_available': resp.is_available,
            'last_update': resp.last_location_update.isoformat() if resp.last_location_update else None,
        } for resp in on_duty_responders],
        'departments': [{
            'id': dept.id,
            'name': dept.name,
            'type': dept.type,
            'latitude': float(dept.headquarters_lat),
            'longitude': float(dept.headquarters_lng),
            'active_incidents': dept.current_active_incidents,
            'available_capacity': dept.available_capacity,
        } for dept in departments],
    }), 200


# ==================== Department Management ====================

@bp.route('/departments/', methods=['GET'])
@department_required
def list_departments(user):
    """List all departments with status"""
    dept_type = request.args.get('type')
    
    query = Department.query.filter(Department.is_active == True)
    
    if dept_type:
        query = query.filter(Department.type == dept_type)
    
    departments = query.order_by(Department.name).all()
    
    # Enhance with responder counts
    results = []
    for dept in departments:
        on_duty = User.query.filter(
            User.department_id == dept.id,
            User.is_responder == True,
            User.is_on_duty == True
        ).count()
        
        available = User.query.filter(
            User.department_id == dept.id,
            User.is_responder == True,
            User.is_on_duty == True,
            User.is_available == True
        ).count()
        
        schema = DepartmentSchema()
        result = schema.dump(dept)
        result['responders_on_duty'] = on_duty
        result['responders_available'] = available
        results.append(result)
    
    return jsonify(results), 200


@bp.route('/departments/<int:id>/', methods=['GET'])
@department_required
def get_department(user, id):
    """Get department details"""
    department = Department.query.get(id)
    
    if not department:
        return jsonify({'detail': 'Not found.'}), 404
    
    schema = DepartmentSchema()
    result = schema.dump(department)
    
    # Include responders
    responders = User.query.filter(
        User.department_id == department.id,
        User.is_responder == True
    ).all()
    
    result['responders'] = [{
        'id': r.id,
        'name': r.full_name,
        'is_on_duty': r.is_on_duty,
        'is_available': r.is_available,
    } for r in responders]
    
    # Include active assignments
    active_assignments = IncidentAssignment.query.filter(
        IncidentAssignment.department_id == department.id,
        IncidentAssignment.status.in_(AssignmentStatus.ACTIVE_STATUSES)
    ).all()
    
    assignment_schema = AssignmentListSchema(many=True)
    result['active_assignments'] = assignment_schema.dump(active_assignments)
    
    return jsonify(result), 200


@bp.route('/departments/', methods=['POST'])
@department_or_admin_required
def create_department(user):
    """Create a new department"""
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    schema = DepartmentCreateSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    # Check if code already exists
    if Department.query.filter_by(code=data['code']).first():
        return jsonify({'code': ['Department with this code already exists.']}), 400
    
    department = Department(**data)
    db.session.add(department)
    db.session.commit()
    
    response_schema = DepartmentSchema()
    return jsonify(response_schema.dump(department)), 201


# ==================== Alerts ====================

@bp.route('/alerts/', methods=['POST'])
@department_required
def create_alert(user):
    """Create a safety alert"""
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    schema = SafetyAlertCreateSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    alert = SafetyAlert(
        created_by_id=user.id,
        **data
    )
    db.session.add(alert)
    db.session.commit()
    
    # Broadcast alert
    broadcast_safety_alert(alert)
    
    # Send notifications
    notification_service = NotificationService()
    notification_service.broadcast_safety_alert(alert)
    
    response_schema = SafetyAlertSchema()
    return jsonify(response_schema.dump(alert)), 201


# ==================== Statistics & Analytics ====================

@bp.route('/stats/', methods=['GET'])
@department_required
def get_stats(user):
    """Get department dashboard statistics"""
    today = datetime.utcnow().date()
    
    # Active incidents by status
    status_counts = db.session.query(
        IncidentReport.status,
        func.count(IncidentReport.id)
    ).filter(
        IncidentReport.status.in_(IncidentStatus.ACTIVE_STATUSES)
    ).group_by(IncidentReport.status).all()
    
    # Active incidents by severity
    severity_counts = db.session.query(
        IncidentReport.severity,
        func.count(IncidentReport.id)
    ).filter(
        IncidentReport.status.in_(IncidentStatus.ACTIVE_STATUSES)
    ).group_by(IncidentReport.severity).all()
    
    # Today's stats
    new_today = IncidentReport.query.filter(
        func.date(IncidentReport.created_at) == today
    ).count()
    
    resolved_today = IncidentReport.query.filter(
        IncidentReport.status == 'RESOLVED',
        func.date(IncidentReport.resolution_time) == today
    ).count()
    
    # SLA breaches
    sla_breached = IncidentReport.query.filter(
        IncidentReport.status.in_(IncidentStatus.ACTIVE_STATUSES)
    ).all()
    sla_breached_count = sum(1 for inc in sla_breached if inc.is_sla_breached)
    
    # Department-specific stats
    my_respondents = User.query.filter(
        User.department_id == user.department_id,
        User.is_responder == True
    ).count()
    
    my_respondents_on_duty = User.query.filter(
        User.department_id == user.department_id,
        User.is_responder == True,
        User.is_on_duty == True
    ).count()
    
    my_active_assignments = IncidentAssignment.query.filter(
        IncidentAssignment.department_id == user.department_id,
        IncidentAssignment.status.in_(AssignmentStatus.ACTIVE_STATUSES)
    ).count()
    
    return jsonify({
        'active_incidents': {
            'by_status': {s: c for s, c in status_counts},
            'by_severity': {s: c for s, c in severity_counts},
            'total': sum(c for _, c in status_counts),
        },
        'today': {
            'new_incidents': new_today,
            'resolved_incidents': resolved_today,
        },
        'sla': {
            'breached_count': sla_breached_count,
        },
        'my_department': {
            'total_respondents': my_respondents,
            'respondents_on_duty': my_respondents_on_duty,
            'active_assignments': my_active_assignments,
        }
    }), 200


@bp.route('/analytics/summary/', methods=['GET'])
@department_required
def department_analytics_summary(user):
    """Get analytics summary for department's department only"""
    if not user.department_id:
        return jsonify({'detail': 'Department user must be assigned to a department.'}), 400
    
    stats = get_department_summary_stats(user.department_id)
    return jsonify(stats), 200


@bp.route('/analytics/timeseries/', methods=['GET'])
@department_required
def department_analytics_timeseries(user):
    """Get analytics time series data for department's department only"""
    if not user.department_id:
        return jsonify({'detail': 'Department user must be assigned to a department.'}), 400
    
    days = request.args.get('days', 30, type=int)
    
    # Limit to 1 year
    if days > 365:
        days = 365
    if days < 1:
        days = 1
    
    data = get_department_timeseries_data(user.department_id, days=days)
    return jsonify(data), 200

