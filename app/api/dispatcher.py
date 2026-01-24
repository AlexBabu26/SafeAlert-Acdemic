"""
Dispatcher API endpoints
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
from app.utils.permissions import dispatcher_required, dispatcher_or_admin_required
from app.services.allocation import AllocationService, get_nearby_departments
from app.services.escalation import EscalationService
from app.services.notification import NotificationService
from app.socketio_events import broadcast_incident_updated, broadcast_assignment_created, broadcast_safety_alert

bp = Blueprint('dispatcher', __name__)


@bp.route('/incidents/', methods=['GET'])
@dispatcher_required
def list_incidents(user):
    """List all active incidents for dispatcher view"""
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
        'next': f'/api/dispatcher/incidents/?page={page + 1}' if page * per_page < total else None,
        'previous': f'/api/dispatcher/incidents/?page={page - 1}' if page > 1 else None,
        'results': schema.dump(incidents)
    }), 200


@bp.route('/incidents/<int:id>/', methods=['GET'])
@dispatcher_required
def get_incident(user, id):
    """Get incident details for dispatcher"""
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
@dispatcher_required
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
@dispatcher_required
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
        source='DISPATCHER'
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
@dispatcher_required
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


@bp.route('/map/', methods=['GET'])
@dispatcher_required
def get_map_data(user):
    """Get real-time map data for dispatcher command center"""
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


@bp.route('/departments/', methods=['GET'])
@dispatcher_required
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
@dispatcher_required
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
@dispatcher_or_admin_required
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


@bp.route('/alerts/', methods=['POST'])
@dispatcher_required
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


@bp.route('/stats/', methods=['GET'])
@dispatcher_required
def get_stats(user):
    """Get dispatcher dashboard statistics"""
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
        }
    }), 200

