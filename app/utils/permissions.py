"""
Permission decorators for Flask routes
"""
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, IncidentReport, IncidentAssignment


def get_current_user():
    """Get the current user from JWT token"""
    current_user_id = get_jwt_identity()
    if current_user_id:
        return User.query.get(int(current_user_id))
    return None


def admin_required(f):
    """Decorator to require admin (is_staff=True) access"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user or not user.is_staff:
            return jsonify({'detail': 'You do not have permission to perform this action.'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def responder_required(f):
    """Decorator to require responder access"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            return jsonify({'detail': 'Authentication credentials were not provided.'}), 401
        
        if not user.is_responder:
            return jsonify({'detail': 'Responder access required.'}), 403
        
        return f(user, *args, **kwargs)
    
    return decorated_function


def dispatcher_required(f):
    """Decorator to require dispatcher access"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            return jsonify({'detail': 'Authentication credentials were not provided.'}), 401
        
        if not user.is_dispatcher and not user.is_staff:
            return jsonify({'detail': 'Dispatcher access required.'}), 403
        
        return f(user, *args, **kwargs)
    
    return decorated_function


def dispatcher_or_admin_required(f):
    """Decorator to require dispatcher or admin access"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            return jsonify({'detail': 'Authentication credentials were not provided.'}), 401
        
        if not user.is_dispatcher and not user.is_staff:
            return jsonify({'detail': 'Dispatcher or admin access required.'}), 403
        
        return f(user, *args, **kwargs)
    
    return decorated_function


def assignment_owner_required(f):
    """Decorator to require ownership of an assignment (responder assigned to it)"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            return jsonify({'detail': 'Authentication credentials were not provided.'}), 401
        
        assignment_id = kwargs.get('assignment_id') or kwargs.get('id')
        if assignment_id:
            assignment = IncidentAssignment.query.get(assignment_id)
            if not assignment:
                return jsonify({'detail': 'Assignment not found.'}), 404
            
            # Dispatchers and admins can access any assignment
            if user.is_dispatcher or user.is_staff:
                return f(user, assignment, *args, **kwargs)
            
            # Responder must be in the assigned department
            if user.is_responder and user.department_id == assignment.department_id:
                return f(user, assignment, *args, **kwargs)
            
            return jsonify({'detail': 'You do not have permission to access this assignment.'}), 403
        
        return f(user, None, *args, **kwargs)
    
    return decorated_function


def owner_required(f):
    """Decorator to require ownership of a resource"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            return jsonify({'detail': 'Authentication credentials were not provided.'}), 401
        
        # Check if this is for an incident
        incident_id = kwargs.get('id') or kwargs.get('incident_id')
        if incident_id:
            incident = IncidentReport.query.get(incident_id)
            if not incident:
                return jsonify({'detail': 'Not found.'}), 404
            
            # Admin, dispatcher can access any incident
            if user.is_staff or user.is_dispatcher:
                return f(user, *args, **kwargs)
            
            # Responder can access incidents assigned to their department
            if user.is_responder and user.department_id:
                if incident.assignments.filter_by(department_id=user.department_id).first():
                    return f(user, *args, **kwargs)
            
            # Users can only access their own
            if incident.user_id != user.id:
                return jsonify({'detail': 'You do not have permission to perform this action.'}), 403
        
        return f(user, *args, **kwargs)
    
    return decorated_function


def can_view_incident(incident_id, user):
    """Check if user can view an incident"""
    incident = IncidentReport.query.get(incident_id)
    if not incident:
        return False, jsonify({'detail': 'Not found.'}), 404
    
    # Admin/dispatcher can view all
    if user.is_staff or user.is_dispatcher:
        return True, None, None
    
    # Responder can view incidents assigned to their department
    if user.is_responder and user.department_id:
        if incident.assignments.filter_by(department_id=user.department_id).first():
            return True, None, None
    
    # User can view their own
    if incident.user_id == user.id:
        return True, None, None
    
    return False, jsonify({'detail': 'You do not have permission to view this incident.'}), 403


def can_view_incident_messages(incident_id, user):
    """Check if user can view messages for an incident"""
    incident = IncidentReport.query.get(incident_id)
    if not incident:
        return False, jsonify({'detail': 'Not found.'}), 404
    
    # Admin/dispatcher can view all
    if user.is_staff or user.is_dispatcher:
        return True, None, None
    
    # Responder can view messages for incidents assigned to their department
    if user.is_responder and user.department_id:
        if incident.assignments.filter_by(department_id=user.department_id).first():
            return True, None, None
    
    # User can view their own
    if incident.user_id == user.id:
        return True, None, None
    
    return False, jsonify({'detail': 'You do not have permission to view messages for this incident.'}), 403


def can_send_message(incident_id, user):
    """Check if user can send messages for an incident"""
    incident = IncidentReport.query.get(incident_id)
    if not incident:
        return False, jsonify({'detail': 'Not found.'}), 404
    
    # Admin/dispatcher can always send
    if user.is_staff or user.is_dispatcher:
        return True, None, None
    
    # Responder can send to incidents assigned to their department
    if user.is_responder and user.department_id:
        if incident.assignments.filter_by(department_id=user.department_id).first():
            return True, None, None
    
    # Users can send to their own incidents
    if incident.user_id == user.id:
        return True, None, None
    
    return False, jsonify({'detail': 'You do not have permission to send messages to this incident.'}), 403
