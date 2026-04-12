"""
Responder API endpoints
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from datetime import datetime, timedelta
from sqlalchemy import func

from app.extensions import db
from app.models import (
    User, 
    IncidentReport, 
    IncidentAssignment, 
    AssignmentStatus,
    Department,
)
from app.schemas.assignment import (
    AssignmentListSchema, 
    AssignmentDetailSchema, 
    AssignmentStatusUpdateSchema,
    IncidentAssignmentSchema,
)
from app.schemas.incident import IncidentReportSchema
from app.utils.permissions import responder_required, assignment_owner_required
from app.utils.validators import validate_latitude, validate_longitude
from app.services.notification import NotificationService
from app.socketio_events import broadcast_assignment_status_changed, broadcast_incident_updated

bp = Blueprint('responder', __name__)


@bp.route('/dashboard/', methods=['GET'])
@responder_required
def dashboard(user):
    """Get responder dashboard data"""
    if not user.department_id:
        return jsonify({'detail': 'No department assigned.'}), 400
    
    # Get assignment stats
    today = datetime.utcnow().date()
    
    # Active assignments for user's department
    active_assignments = IncidentAssignment.query.filter(
        IncidentAssignment.department_id == user.department_id,
        IncidentAssignment.status.in_(AssignmentStatus.ACTIVE_STATUSES)
    ).count()
    
    # Completed today
    completed_today = IncidentAssignment.query.filter(
        IncidentAssignment.department_id == user.department_id,
        IncidentAssignment.status == AssignmentStatus.COMPLETED,
        func.date(IncidentAssignment.completed_at) == today
    ).count()
    
    # Average response time (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    avg_response = db.session.query(
        func.avg(IncidentAssignment.total_response_time_seconds)
    ).filter(
        IncidentAssignment.department_id == user.department_id,
        IncidentAssignment.status == AssignmentStatus.COMPLETED,
        IncidentAssignment.completed_at >= week_ago,
        IncidentAssignment.total_response_time_seconds.isnot(None)
    ).scalar()
    
    # My personal stats
    my_active = IncidentAssignment.query.filter(
        IncidentAssignment.responder_id == user.id,
        IncidentAssignment.status.in_(AssignmentStatus.ACTIVE_STATUSES)
    ).count()
    
    my_completed_today = IncidentAssignment.query.filter(
        IncidentAssignment.responder_id == user.id,
        IncidentAssignment.status == AssignmentStatus.COMPLETED,
        func.date(IncidentAssignment.completed_at) == today
    ).count()
    
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'department_id': user.department_id,
            'department_name': user.department.name if user.department else None,
            'is_on_duty': user.is_on_duty,
            'is_available': user.is_available,
        },
        'department_stats': {
            'active_assignments': active_assignments,
            'completed_today': completed_today,
            'avg_response_time_minutes': round(avg_response / 60, 1) if avg_response else None,
        },
        'my_stats': {
            'active_assignments': my_active,
            'completed_today': my_completed_today,
        }
    }), 200


@bp.route('/assignments/', methods=['GET'])
@responder_required
def list_assignments(user):
    """List assignments for responder's department"""
    if not user.department_id:
        return jsonify({'detail': 'No department assigned.'}), 400
    
    # Filter parameters
    status = request.args.get('status')
    mine_only = request.args.get('mine_only', 'false').lower() == 'true'
    
    # Base query
    query = IncidentAssignment.query.filter(
        IncidentAssignment.department_id == user.department_id
    )
    
    # Filter by status
    if status:
        query = query.filter(IncidentAssignment.status == status)
    else:
        # Default: show active assignments
        query = query.filter(IncidentAssignment.status.in_(AssignmentStatus.ACTIVE_STATUSES))
    
    # Filter to my assignments only
    if mine_only:
        query = query.filter(IncidentAssignment.responder_id == user.id)
    
    # Order by priority and time
    query = query.order_by(
        IncidentAssignment.priority_rank,
        IncidentAssignment.assigned_at.desc()
    )
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('PAGINATION_PER_PAGE', 20)
    
    total = query.count()
    assignments = query.offset((page - 1) * per_page).limit(per_page).all()
    
    schema = AssignmentListSchema(many=True)
    
    return jsonify({
        'count': total,
        'next': f'/api/responder/assignments/?page={page + 1}' if page * per_page < total else None,
        'previous': f'/api/responder/assignments/?page={page - 1}' if page > 1 else None,
        'results': schema.dump(assignments)
    }), 200


@bp.route('/assignments/<int:id>/', methods=['GET'])
@assignment_owner_required
def get_assignment(user, assignment, id):
    """Get assignment details"""
    schema = AssignmentDetailSchema()
    return jsonify(schema.dump(assignment)), 200


@bp.route('/assignments/<int:id>/accept/', methods=['POST'])
@assignment_owner_required
def accept_assignment(user, assignment, id):
    """Accept an assignment"""
    if assignment.status != AssignmentStatus.ASSIGNED:
        return jsonify({'detail': f'Cannot accept assignment in {assignment.status} status.'}), 400
    
    # Accept the assignment
    assignment.accept(responder_id=user.id)
    
    # Update incident status
    incident = assignment.incident
    if incident.status == 'DISPATCHED':
        incident.acknowledge()
    
    # Mark responder as busy
    user.mark_busy()
    
    db.session.commit()
    
    # Broadcast updates
    broadcast_assignment_status_changed(assignment, 'ASSIGNED', 'ACCEPTED')
    broadcast_incident_updated(incident)
    
    # Notify
    notification_service = NotificationService()
    notification_service.notify_status_change(incident, 'DISPATCHED', 'ACKNOWLEDGED')
    
    schema = IncidentAssignmentSchema()
    return jsonify(schema.dump(assignment)), 200


@bp.route('/assignments/<int:id>/status/', methods=['POST'])
@assignment_owner_required
def update_assignment_status(user, assignment, id):
    """Update assignment status"""
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    schema = AssignmentStatusUpdateSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    new_status = data['status']
    old_status = assignment.status
    
    # Validate status transition
    valid_transitions = {
        AssignmentStatus.ASSIGNED: [AssignmentStatus.ACCEPTED, AssignmentStatus.DECLINED],
        AssignmentStatus.ACCEPTED: [AssignmentStatus.EN_ROUTE, AssignmentStatus.DECLINED],
        AssignmentStatus.EN_ROUTE: [AssignmentStatus.ON_SCENE],
        AssignmentStatus.ON_SCENE: [AssignmentStatus.COMPLETED],
    }
    
    if old_status in valid_transitions and new_status not in valid_transitions.get(old_status, []):
        return jsonify({'detail': f'Cannot transition from {old_status} to {new_status}.'}), 400
    
    # Update assignment status
    if new_status == AssignmentStatus.ACCEPTED:
        assignment.accept(responder_id=user.id)
    elif new_status == AssignmentStatus.EN_ROUTE:
        assignment.mark_en_route()
    elif new_status == AssignmentStatus.ON_SCENE:
        assignment.mark_arrived()
    elif new_status == AssignmentStatus.COMPLETED:
        assignment.complete(notes=data.get('notes'))
        user.mark_available()
    elif new_status == AssignmentStatus.DECLINED:
        assignment.decline(reason=data.get('decline_reason'))
    
    # Update incident status based on assignment status
    incident = assignment.incident
    status_mapping = {
        AssignmentStatus.ACCEPTED: 'ACKNOWLEDGED',
        AssignmentStatus.EN_ROUTE: 'EN_ROUTE',
        AssignmentStatus.ON_SCENE: 'ON_SCENE',
    }
    
    if new_status in status_mapping:
        old_incident_status = incident.status
        if new_status == AssignmentStatus.EN_ROUTE:
            incident.mark_en_route()
        elif new_status == AssignmentStatus.ON_SCENE:
            incident.mark_on_scene()
        elif new_status == AssignmentStatus.ACCEPTED:
            incident.acknowledge()
    
    db.session.commit()
    
    # Broadcast updates
    broadcast_assignment_status_changed(assignment, old_status, new_status)
    broadcast_incident_updated(incident)
    
    # Notify status change
    notification_service = NotificationService()
    notification_service.notify_status_change(incident, old_status, new_status)
    
    response_schema = IncidentAssignmentSchema()
    return jsonify(response_schema.dump(assignment)), 200


@bp.route('/location/', methods=['POST'])
@responder_required
def update_location(user):
    """Update responder's current location"""
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    latitude = request.json.get('latitude')
    longitude = request.json.get('longitude')
    
    if latitude is None or longitude is None:
        return jsonify({'detail': 'Latitude and longitude required.'}), 400

    try:
        validate_latitude(latitude)
        validate_longitude(longitude)
    except Exception as e:
        return jsonify({'detail': str(e)}), 400

    user.update_location(latitude, longitude)
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'latitude': str(latitude),
        'longitude': str(longitude),
        'updated_at': user.last_location_update.isoformat()
    }), 200


@bp.route('/duty/', methods=['POST'])
@responder_required
def toggle_duty(user):
    """Toggle on-duty status"""
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    is_on_duty = request.json.get('is_on_duty')
    
    if is_on_duty is None:
        return jsonify({'detail': 'is_on_duty required.'}), 400
    
    if is_on_duty:
        user.go_on_duty()
    else:
        user.go_off_duty()
    
    db.session.commit()
    
    return jsonify({
        'is_on_duty': user.is_on_duty,
        'is_available': user.is_available,
    }), 200


@bp.route('/stats/', methods=['GET'])
@responder_required
def get_stats(user):
    """Get responder's personal statistics"""
    # Time range
    days = request.args.get('days', 30, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    
    # Total assignments
    total = IncidentAssignment.query.filter(
        IncidentAssignment.responder_id == user.id,
        IncidentAssignment.assigned_at >= since
    ).count()
    
    # Completed assignments
    completed = IncidentAssignment.query.filter(
        IncidentAssignment.responder_id == user.id,
        IncidentAssignment.status == AssignmentStatus.COMPLETED,
        IncidentAssignment.completed_at >= since
    ).count()
    
    # Average response time
    avg_response = db.session.query(
        func.avg(IncidentAssignment.total_response_time_seconds)
    ).filter(
        IncidentAssignment.responder_id == user.id,
        IncidentAssignment.status == AssignmentStatus.COMPLETED,
        IncidentAssignment.completed_at >= since,
        IncidentAssignment.total_response_time_seconds.isnot(None)
    ).scalar()
    
    # Fastest response
    fastest = db.session.query(
        func.min(IncidentAssignment.total_response_time_seconds)
    ).filter(
        IncidentAssignment.responder_id == user.id,
        IncidentAssignment.status == AssignmentStatus.COMPLETED,
        IncidentAssignment.completed_at >= since,
        IncidentAssignment.total_response_time_seconds.isnot(None)
    ).scalar()
    
    return jsonify({
        'period_days': days,
        'total_assignments': total,
        'completed_assignments': completed,
        'completion_rate': round(completed / total * 100, 1) if total > 0 else 0,
        'avg_response_time_minutes': round(avg_response / 60, 1) if avg_response else None,
        'fastest_response_minutes': round(fastest / 60, 1) if fastest else None,
    }), 200

