"""
WebSocket event handlers for SafeAlert real-time features
"""
from datetime import datetime
from flask import request
from flask_socketio import emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token, get_jwt_identity

from app.extensions import socketio, db
from app.models import User, IncidentReport, IncidentMessage


def get_user_from_token(token):
    """Extract user from JWT token"""
    try:
        decoded = decode_token(token)
        user_id = decoded.get('sub')
        if user_id:
            return User.query.get(int(user_id))
    except Exception:
        pass
    return None


# ==================== Connection Events ====================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    # Client should authenticate immediately after connecting
    emit('connected', {'status': 'connected', 'sid': request.sid})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    pass  # Cleanup handled automatically


@socketio.on('authenticate')
def handle_authenticate(data):
    """
    Authenticate the WebSocket connection with JWT token.
    
    Expected data: {'token': 'jwt_access_token'}
    """
    token = data.get('token')
    if not token:
        emit('auth_error', {'message': 'Token required'})
        return
    
    user = get_user_from_token(token)
    if not user:
        emit('auth_error', {'message': 'Invalid token'})
        return
    
    # Join user-specific room for personal notifications
    join_room(f'user_{user.id}')
    
    # Join role-specific rooms
    if user.is_staff:
        join_room('admins')
    if user.is_dispatcher:
        join_room('dispatchers')
    if user.is_responder:
        join_room('responders')
        if user.department_id:
            join_room(f'department_{user.department_id}')
    
    emit('authenticated', {
        'user_id': user.id,
        'username': user.username,
        'roles': {
            'is_staff': user.is_staff,
            'is_dispatcher': user.is_dispatcher,
            'is_responder': user.is_responder
        }
    })


# ==================== Incident Room Events ====================

@socketio.on('join_incident')
def handle_join_incident(data):
    """
    Join an incident room to receive updates.
    
    Expected data: {'incident_id': 123, 'token': 'jwt_token'}
    """
    token = data.get('token')
    incident_id = data.get('incident_id')
    
    if not token or not incident_id:
        emit('error', {'message': 'Token and incident_id required'})
        return
    
    user = get_user_from_token(token)
    if not user:
        emit('error', {'message': 'Invalid token'})
        return
    
    incident = IncidentReport.query.get(incident_id)
    if not incident:
        emit('error', {'message': 'Incident not found'})
        return
    
    # Check permission: owner, assigned responder, dispatcher, or admin
    can_access = (
        user.is_staff or 
        user.is_dispatcher or
        incident.user_id == user.id or
        (user.is_responder and incident.assignments.filter_by(department_id=user.department_id).first())
    )
    
    if not can_access:
        emit('error', {'message': 'Access denied'})
        return
    
    room = f'incident_{incident_id}'
    join_room(room)
    
    emit('joined_incident', {
        'incident_id': incident_id,
        'room': room
    })


@socketio.on('leave_incident')
def handle_leave_incident(data):
    """
    Leave an incident room.
    
    Expected data: {'incident_id': 123}
    """
    incident_id = data.get('incident_id')
    if incident_id:
        leave_room(f'incident_{incident_id}')
        emit('left_incident', {'incident_id': incident_id})


# ==================== Responder Location Events ====================

@socketio.on('update_location')
def handle_update_location(data):
    """
    Update responder's current location.
    
    Expected data: {
        'token': 'jwt_token',
        'latitude': 40.7128,
        'longitude': -74.0060,
        'incident_id': 123  # Optional: if en route to incident
    }
    """
    token = data.get('token')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    incident_id = data.get('incident_id')
    
    if not all([token, latitude, longitude]):
        emit('error', {'message': 'Token, latitude, and longitude required'})
        return
    
    user = get_user_from_token(token)
    if not user or not user.is_responder:
        emit('error', {'message': 'Invalid token or not a responder'})
        return
    
    # Update user's location in database
    user.update_location(latitude, longitude)
    db.session.commit()
    
    # If assigned to an incident, broadcast location to incident room
    if incident_id:
        emit('responder_location', {
            'responder_id': user.id,
            'responder_name': user.full_name,
            'latitude': latitude,
            'longitude': longitude,
            'updated_at': datetime.utcnow().isoformat()
        }, room=f'incident_{incident_id}')
    
    # Broadcast to dispatchers
    emit('responder_location', {
        'responder_id': user.id,
        'responder_name': user.full_name,
        'department_id': user.department_id,
        'latitude': latitude,
        'longitude': longitude,
        'updated_at': datetime.utcnow().isoformat()
    }, room='dispatchers')
    
    emit('location_updated', {'status': 'ok'})


# ==================== Real-time Chat Events ====================

@socketio.on('send_message')
def handle_send_message(data):
    """
    Send a chat message on an incident.
    
    Expected data: {
        'token': 'jwt_token',
        'incident_id': 123,
        'message': 'Message text'
    }
    """
    token = data.get('token')
    incident_id = data.get('incident_id')
    message_text = data.get('message')
    
    if not all([token, incident_id, message_text]):
        emit('error', {'message': 'Token, incident_id, and message required'})
        return
    
    user = get_user_from_token(token)
    if not user:
        emit('error', {'message': 'Invalid token'})
        return
    
    incident = IncidentReport.query.get(incident_id)
    if not incident:
        emit('error', {'message': 'Incident not found'})
        return
    
    # Create message in database
    message = IncidentMessage(
        incident_id=incident_id,
        sender_id=user.id,
        message=message_text
    )
    db.session.add(message)
    db.session.commit()
    
    # Broadcast to incident room
    emit('new_message', {
        'id': message.id,
        'incident_id': incident_id,
        'sender_id': user.id,
        'sender_username': user.username,
        'sender_role': 'admin' if user.is_staff else ('responder' if user.is_responder else 'user'),
        'message': message_text,
        'created_at': message.created_at.isoformat()
    }, room=f'incident_{incident_id}')
    
    emit('message_sent', {'message_id': message.id})


@socketio.on('typing')
def handle_typing(data):
    """
    Broadcast typing indicator.
    
    Expected data: {
        'token': 'jwt_token',
        'incident_id': 123,
        'is_typing': True/False
    }
    """
    token = data.get('token')
    incident_id = data.get('incident_id')
    is_typing = data.get('is_typing', False)
    
    user = get_user_from_token(token)
    if not user or not incident_id:
        return
    
    emit('user_typing', {
        'user_id': user.id,
        'username': user.username,
        'is_typing': is_typing
    }, room=f'incident_{incident_id}', include_self=False)


# ==================== Broadcast Functions (called from services) ====================

def broadcast_incident_created(incident):
    """Broadcast new incident to dispatchers"""
    socketio.emit('incident_created', {
        'id': incident.id,
        'title': incident.title,
        'severity': incident.severity,
        'status': incident.status,
        'category_name': incident.category.name if incident.category else None,
        'latitude': float(incident.latitude) if incident.latitude else None,
        'longitude': float(incident.longitude) if incident.longitude else None,
        'created_at': incident.created_at.isoformat()
    }, room='dispatchers')


def broadcast_incident_updated(incident):
    """Broadcast incident update to relevant parties"""
    data = {
        'id': incident.id,
        'status': incident.status,
        'severity': incident.severity,
        'updated_at': incident.updated_at.isoformat()
    }
    
    # To incident room (reporter, assigned responders)
    socketio.emit('incident_updated', data, room=f'incident_{incident.id}')
    
    # To dispatchers
    socketio.emit('incident_updated', data, room='dispatchers')


def broadcast_assignment_created(assignment):
    """Broadcast new assignment to department responders"""
    incident = assignment.incident
    
    socketio.emit('new_assignment', {
        'assignment_id': assignment.id,
        'incident_id': incident.id,
        'incident_title': incident.title,
        'incident_severity': incident.severity,
        'category_name': incident.category.name if incident.category else None,
        'priority_rank': assignment.priority_rank,
        'distance_km': assignment.distance_km,
        'latitude': float(incident.latitude) if incident.latitude else None,
        'longitude': float(incident.longitude) if incident.longitude else None,
        'assigned_at': assignment.assigned_at.isoformat()
    }, room=f'department_{assignment.department_id}')


def broadcast_assignment_status_changed(assignment, old_status, new_status):
    """Broadcast assignment status change"""
    socketio.emit('assignment_status_changed', {
        'assignment_id': assignment.id,
        'incident_id': assignment.incident_id,
        'old_status': old_status,
        'new_status': new_status,
        'updated_at': datetime.utcnow().isoformat()
    }, room=f'incident_{assignment.incident_id}')


def broadcast_to_user(user_id, event, data):
    """Broadcast event to a specific user"""
    socketio.emit(event, data, room=f'user_{user_id}')


def broadcast_safety_alert(alert, room='all'):
    """Broadcast safety alert"""
    socketio.emit('safety_alert', {
        'id': alert.id,
        'title': alert.title,
        'message': alert.message,
        'severity': alert.severity,
        'alert_type': alert.alert_type,
        'center_lat': float(alert.center_lat) if alert.center_lat else None,
        'center_lng': float(alert.center_lng) if alert.center_lng else None,
        'radius_km': alert.radius_km,
        'instructions': alert.instructions,
        'created_at': alert.created_at.isoformat()
    }, room=room)

