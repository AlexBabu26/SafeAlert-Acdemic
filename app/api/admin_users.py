"""
Admin User Management API endpoints
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy import or_

from app.models import User, Department
from app.extensions import db
from app.schemas.user import UserAdminSchema, UserUpdateSchema
from app.utils.permissions import admin_required

bp = Blueprint('admin_users', __name__)


@bp.route('/', methods=['GET'])
@admin_required
def list_users(user):
    """List all users with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Filters
    role = request.args.get('role')  # citizen, responder, dispatcher, admin
    is_active = request.args.get('is_active')
    department_id = request.args.get('department_id', type=int)
    search = request.args.get('search', '')
    
    # Build query
    query = User.query
    
    # Role filter
    if role == 'admin':
        query = query.filter(User.is_staff == True)
    elif role == 'department':
        query = query.filter(User.is_department == True)
    elif role == 'responder':
        query = query.filter(User.is_responder == True)
    elif role == 'citizen':
        query = query.filter(
            User.is_staff == False,
            User.is_department == False,
            User.is_responder == False
        )
    
    # Active status filter
    if is_active is not None:
        is_active_bool = is_active.lower() in ('true', '1', 'yes')
        query = query.filter(User.is_active == is_active_bool)
    
    # Department filter
    if department_id:
        query = query.filter(User.department_id == department_id)
    
    # Search filter
    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            or_(
                User.username.ilike(search_filter),
                User.email.ilike(search_filter),
                User.first_name.ilike(search_filter),
                User.last_name.ilike(search_filter),
                User.badge_number.ilike(search_filter)
            )
        )
    
    # Order by date joined (newest first)
    query = query.order_by(User.date_joined.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    schema = UserAdminSchema(many=True)
    
    return jsonify({
        'results': schema.dump(pagination.items),
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }), 200


@bp.route('/stats/', methods=['GET'])
@admin_required
def user_stats(user):
    """Get user statistics"""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    inactive_users = User.query.filter_by(is_active=False).count()
    
    # Count by role
    admins = User.query.filter_by(is_staff=True).count()
    departments = User.query.filter_by(is_department=True).count()
    responders = User.query.filter_by(is_responder=True).count()
    citizens = User.query.filter(
        User.is_staff == False,
        User.is_department == False,
        User.is_responder == False
    ).count()
    
    # Pending responders (registered but not active)
    pending_responders = User.query.filter(
        User.is_responder == True,
        User.is_active == False
    ).count()
    
    # Responders on duty
    responders_on_duty = User.query.filter(
        User.is_responder == True,
        User.is_on_duty == True
    ).count()
    
    # Pending department users
    pending_departments = User.query.filter(
        User.is_department == True,
        User.is_active == False
    ).count()
    
    # Pending citizens
    pending_citizens = User.query.filter(
        User.is_staff == False,
        User.is_department == False,
        User.is_responder == False,
        User.is_active == False
    ).count()
    
    return jsonify({
        'total': total_users,
        'active': active_users,
        'inactive': inactive_users,
        'by_role': {
            'admins': admins,
            'departments': departments,
            'responders': responders,
            'citizens': citizens
        },
        'pending': {
            'responders': pending_responders,
            'departments': pending_departments,
            'citizens': pending_citizens,
            'total': pending_responders + pending_departments + pending_citizens
        },
        'responders_on_duty': responders_on_duty
    }), 200


@bp.route('/<int:user_id>/', methods=['GET'])
@admin_required
def get_user(user, user_id):
    """Get user details"""
    target_user = User.query.get(user_id)
    if not target_user:
        return jsonify({'detail': 'User not found.'}), 404
    
    schema = UserAdminSchema()
    result = schema.dump(target_user)
    
    # Add department info if applicable
    if target_user.department_id:
        dept = Department.query.get(target_user.department_id)
        if dept:
            result['department_name'] = dept.name
            result['department_type'] = dept.type
    
    return jsonify(result), 200


@bp.route('/<int:user_id>/', methods=['PATCH'])
@admin_required
def update_user(user, user_id):
    """Update user (activate/deactivate, change role, etc.)"""
    target_user = User.query.get(user_id)
    if not target_user:
        return jsonify({'detail': 'User not found.'}), 404
    
    # Prevent admin from deactivating themselves
    if user.id == user_id and request.json.get('is_active') == False:
        return jsonify({'detail': 'You cannot deactivate your own account.'}), 400
    
    schema = UserUpdateSchema()
    try:
        data = schema.load(request.json, partial=True)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    # Validate department if changing
    if 'department_id' in data and data['department_id']:
        dept = Department.query.get(data['department_id'])
        if not dept:
            return jsonify({'department_id': ['Invalid department.']}), 400
    
    # Update fields
    for field, value in data.items():
        setattr(target_user, field, value)
    
    db.session.commit()
    
    result_schema = UserAdminSchema()
    return jsonify({
        'message': 'User updated successfully.',
        'user': result_schema.dump(target_user)
    }), 200


@bp.route('/<int:user_id>/activate/', methods=['POST'])
@admin_required
def activate_user(user, user_id):
    """Activate a user account
    
    For department users, this also activates the associated department/office.
    """
    target_user = User.query.get(user_id)
    if not target_user:
        return jsonify({'detail': 'User not found.'}), 404
    
    if target_user.is_active:
        return jsonify({'detail': 'User is already active.'}), 400
    
    target_user.is_active = True
    
    # If this is a department user, also activate their department
    department_activated = False
    if target_user.is_department and target_user.department_id:
        dept = Department.query.get(target_user.department_id)
        if dept and not dept.is_active:
            dept.is_active = True
            department_activated = True
    
    db.session.commit()
    
    # TODO: Send notification to user about activation
    
    schema = UserAdminSchema()
    message = f'User {target_user.username} has been activated.'
    if department_activated:
        message += f' Department "{dept.name}" has also been activated.'
    
    return jsonify({
        'message': message,
        'user': schema.dump(target_user),
        'department_activated': department_activated
    }), 200


@bp.route('/<int:user_id>/deactivate/', methods=['POST'])
@admin_required
def deactivate_user(user, user_id):
    """Deactivate a user account"""
    target_user = User.query.get(user_id)
    if not target_user:
        return jsonify({'detail': 'User not found.'}), 404
    
    # Prevent admin from deactivating themselves
    if user.id == user_id:
        return jsonify({'detail': 'You cannot deactivate your own account.'}), 400
    
    if not target_user.is_active:
        return jsonify({'detail': 'User is already deactivated.'}), 400
    
    target_user.is_active = False
    target_user.is_on_duty = False  # Take responder off duty
    target_user.is_available = False
    db.session.commit()
    
    schema = UserAdminSchema()
    return jsonify({
        'message': f'User {target_user.username} has been deactivated.',
        'user': schema.dump(target_user)
    }), 200


@bp.route('/<int:user_id>/', methods=['DELETE'])
@admin_required
def delete_user(user, user_id):
    """Delete a user account (soft delete by deactivating, or hard delete)"""
    target_user = User.query.get(user_id)
    if not target_user:
        return jsonify({'detail': 'User not found.'}), 404
    
    # Prevent admin from deleting themselves
    if user.id == user_id:
        return jsonify({'detail': 'You cannot delete your own account.'}), 400
    
    # Check if hard delete is requested
    hard_delete = request.args.get('hard', 'false').lower() == 'true'
    
    if hard_delete:
        # Hard delete - remove from database
        username = target_user.username
        db.session.delete(target_user)
        db.session.commit()
        return jsonify({'message': f'User {username} has been permanently deleted.'}), 200
    else:
        # Soft delete - just deactivate
        target_user.is_active = False
        db.session.commit()
        return jsonify({'message': f'User {target_user.username} has been deactivated.'}), 200


@bp.route('/pending/', methods=['GET'])
@admin_required
def list_pending_users(user):
    """List users pending activation (primarily responders)"""
    users = User.query.filter_by(is_active=False).order_by(User.date_joined.desc()).all()
    
    schema = UserAdminSchema(many=True)
    return jsonify({
        'results': schema.dump(users),
        'total': len(users)
    }), 200


@bp.route('/bulk-activate/', methods=['POST'])
@admin_required
def bulk_activate(user):
    """Bulk activate multiple users"""
    user_ids = request.json.get('user_ids', [])
    
    if not user_ids:
        return jsonify({'detail': 'No user IDs provided.'}), 400
    
    activated = 0
    for user_id in user_ids:
        target_user = User.query.get(user_id)
        if target_user and not target_user.is_active:
            target_user.is_active = True
            activated += 1
    
    db.session.commit()
    
    return jsonify({
        'message': f'{activated} user(s) have been activated.',
        'activated_count': activated
    }), 200

