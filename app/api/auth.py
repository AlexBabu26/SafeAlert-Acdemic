"""
Authentication API endpoints
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app.models import User, Department, DepartmentType
from app.extensions import db
from app.schemas.user import UserRegistrationSchema, UserSchema
import re
import secrets

bp = Blueprint('auth', __name__)


def generate_department_code(department_type, name):
    """Generate a unique department code based on type and name"""
    type_prefixes = {
        'FIRE': 'FD',
        'POLICE': 'PD',
        'MEDICAL': 'MD',
        'RESCUE': 'RS',
        'HAZMAT': 'HZ',
        'TRAFFIC': 'TR',
    }
    prefix = type_prefixes.get(department_type, 'DP')
    
    # Count existing departments of this type
    count = Department.query.filter_by(type=department_type).count()
    
    return f"{prefix}-{count + 1:03d}"


@bp.route('/register/', methods=['POST'])
def register():
    """User registration endpoint - supports citizen, responder, and department registration
    
    All users require admin approval before they can login.
    
    - Citizen: Basic user who can report incidents
    - Responder: Field worker who joins an existing department
    - Department: Registers a new department/office (e.g., Police Station, Fire Station)
    """
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    schema = UserRegistrationSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    # Check if username already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'username': ['A user with that username already exists.']}), 400
    
    # Check if email already exists (if provided)
    if data.get('email') and User.query.filter_by(email=data['email']).first():
        return jsonify({'email': ['A user with that email already exists.']}), 400
    
    role = data.get('role', 'citizen')
    department = None
    new_department = None
    
    # Handle responder registration - joins existing department
    if role == 'responder':
        department = Department.query.get(data.get('department_id'))
        if not department:
            return jsonify({'department_id': ['Please select a valid department to join.']}), 400
        if not department.is_active:
            return jsonify({'department_id': ['This department is not currently accepting new respondents.']}), 400
    
    # Handle department registration - creates a new department/office
    if role == 'department':
        department_type = data.get('department_type')
        if department_type not in DepartmentType.CHOICES:
            return jsonify({'department_type': [f'Invalid department type. Must be one of: {", ".join(DepartmentType.CHOICES)}']}), 400
        
        # Generate department code if not provided
        department_code = data.get('department_code') or generate_department_code(department_type, data.get('department_name'))
        
        # Check for duplicate department code
        if Department.query.filter_by(code=department_code).first():
            return jsonify({'department_code': ['A department with this code already exists.']}), 400
        
        # Create the new department/office
        new_department = Department(
            name=data.get('department_name'),
            code=department_code,
            type=department_type,
            description=f"Registered via SafeAlert - {data.get('department_name')}",
            headquarters_lat=data.get('latitude'),
            headquarters_lng=data.get('longitude'),
            address=data.get('address', ''),
            is_active=False,  # Department also needs admin approval
        )
        db.session.add(new_department)
        db.session.flush()  # Get the ID without committing
        department = new_department
    
    # Create user based on role
    user = User(
        username=data['username'],
        email=data.get('email', ''),
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        phone_number=data.get('phone_number', ''),
        is_responder=(role == 'responder'),
        is_department=(role == 'department'),
        department_id=department.id if department else None,
        badge_number=data.get('badge_number') if role == 'responder' else None,
        is_active=False,  # All users need admin approval
    )
    
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    user_schema = UserSchema()
    
    # Return appropriate message based on role
    role_messages = {
        'citizen': 'Your account has been created and is pending approval. You will be notified once your account is activated by an administrator.',
        'responder': f'Your respondent account has been created and is pending approval to join {department.name}. You will be notified once your account is activated.',
        'department': f'Your department "{new_department.name}" has been registered and is pending approval. Both the department and your account will be activated by an administrator.',
    }
    
    return jsonify({
        'user': user_schema.dump(user),
        'message': role_messages.get(role, role_messages['citizen']),
        'pending_approval': True,
        'department': {
            'id': new_department.id,
            'name': new_department.name,
            'code': new_department.code,
            'type': new_department.type,
        } if new_department else None,
    }), 201


@bp.route('/departments/', methods=['GET'])
def list_departments_for_registration():
    """Get list of departments for responder registration
    
    Returns only active departments that respondents can join.
    """
    departments = Department.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'type': d.type,
        'type_display': d.type.replace('_', ' ').title(),
        'address': d.address or 'No address provided',
    } for d in departments]), 200


@bp.route('/department-types/', methods=['GET'])
def list_department_types():
    """Get list of available department types for department registration
    
    Used when registering a new department/office.
    """
    type_info = {
        'FIRE': {'name': 'Fire & Rescue', 'icon': '🔥', 'description': 'Fire stations and rescue units'},
        'POLICE': {'name': 'Police', 'icon': '👮', 'description': 'Police stations and law enforcement'},
        'MEDICAL': {'name': 'Medical', 'icon': '🏥', 'description': 'Hospitals, ambulance services, and medical facilities'},
        'RESCUE': {'name': 'Rescue', 'icon': '🚁', 'description': 'Search and rescue teams'},
        'HAZMAT': {'name': 'Hazmat', 'icon': '☢️', 'description': 'Hazardous materials response teams'},
        'TRAFFIC': {'name': 'Traffic', 'icon': '🚗', 'description': 'Traffic control and road safety'},
    }
    
    return jsonify([{
        'type': t,
        'name': type_info.get(t, {}).get('name', t.title()),
        'icon': type_info.get(t, {}).get('icon', '🏢'),
        'description': type_info.get(t, {}).get('description', ''),
    } for t in DepartmentType.CHOICES]), 200


@bp.route('/areas/', methods=['GET'])
def list_predefined_areas():
    """Get predefined areas for location selection during registration"""
    # Predefined areas for UAE/Sharjah region
    areas = [
        {
            'id': 'sharjah_downtown',
            'name': 'Sharjah Downtown',
            'latitude': 25.3463,
            'longitude': 55.4209,
        },
        {
            'id': 'al_majaz',
            'name': 'Al Majaz',
            'latitude': 25.3205,
            'longitude': 55.3786,
        },
        {
            'id': 'al_nahda',
            'name': 'Al Nahda',
            'latitude': 25.3008,
            'longitude': 55.3756,
        },
        {
            'id': 'al_qasimia',
            'name': 'Al Qasimia',
            'latitude': 25.3590,
            'longitude': 55.3909,
        },
        {
            'id': 'muwaileh',
            'name': 'Muwaileh',
            'latitude': 25.2926,
            'longitude': 55.4639,
        },
        {
            'id': 'al_khan',
            'name': 'Al Khan',
            'latitude': 25.3374,
            'longitude': 55.3753,
        },
        {
            'id': 'university_city',
            'name': 'University City',
            'latitude': 25.2951,
            'longitude': 55.4877,
        },
        {
            'id': 'industrial_area',
            'name': 'Industrial Area',
            'latitude': 25.3284,
            'longitude': 55.4006,
        },
    ]
    return jsonify(areas), 200


@bp.route('/token/', methods=['POST'])
def login():
    """JWT token obtain endpoint (login)
    
    Supports login with either username or email address.
    """
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    username_or_email = request.json.get('username')
    password = request.json.get('password')
    
    if not username_or_email or not password:
        return jsonify({'detail': 'Username and password required.'}), 400
    
    # Find user by username OR email
    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()
    
    if not user or not user.check_password(password):
        return jsonify({'detail': 'No active account found with the given credentials'}), 401
    
    # Check if user account is active
    if not user.is_active:
        return jsonify({'detail': 'Your account is pending approval or has been deactivated. Please contact an administrator.'}), 403
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Generate tokens (identity must be string for Flask-JWT-Extended)
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    return jsonify({
        'access': access_token,
        'refresh': refresh_token,
    }), 200


@bp.route('/token/refresh/', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    current_user_id = get_jwt_identity()  # Returns string from JWT
    access_token = create_access_token(identity=str(current_user_id))
    
    return jsonify({
        'access': access_token,
    }), 200


@bp.route('/me/', methods=['GET'])
@jwt_required()
def me():
    """Get current user profile"""
    current_user_id = get_jwt_identity()  # Returns string from JWT
    user = User.query.get(int(current_user_id))
    
    if not user:
        return jsonify({'detail': 'User not found.'}), 404
    
    schema = UserSchema()
    return jsonify(schema.dump(user)), 200


@bp.route('/forgot-password/', methods=['POST'])
def forgot_password():
    """Request password reset - generates a reset token
    
    Simple implementation: Check if email exists, generate token, return success.
    In production, you would send an email with the reset link.
    """
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    email = request.json.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'email': ['Email is required.']}), 400
    
    # Find user by email
    user = User.query.filter_by(email=email).first()
    
    if not user:
        # Don't reveal if email exists or not for security
        return jsonify({
            'message': 'If an account with that email exists, a password reset link has been sent.',
            'token': None  # No token if user doesn't exist
        }), 200
    
    # Generate a secure random token
    reset_token = secrets.token_urlsafe(32)
    
    # Set token expiry (1 hour from now)
    user.reset_token = reset_token
    user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()
    
    # In production, send email here with reset link
    # For now, return the token in the response (for testing/demo purposes)
    return jsonify({
        'message': 'If an account with that email exists, a password reset link has been sent.',
        'token': reset_token,  # Remove this in production
        'reset_url': f'/reset-password?token={reset_token}'  # Remove this in production
    }), 200


@bp.route('/reset-password/', methods=['POST'])
def reset_password():
    """Reset password using token
    
    Validates the token and updates the user's password.
    """
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    token = request.json.get('token', '').strip()
    new_password = request.json.get('new_password', '')
    
    if not token:
        return jsonify({'token': ['Reset token is required.']}), 400
    
    if not new_password:
        return jsonify({'new_password': ['New password is required.']}), 400
    
    if len(new_password) < 8:
        return jsonify({'new_password': ['Password must be at least 8 characters.']}), 400
    
    # Find user by token
    user = User.query.filter_by(reset_token=token).first()
    
    if not user:
        return jsonify({'detail': 'Invalid or expired reset token.'}), 400
    
    # Check if token is expired
    if user.reset_token_expiry < datetime.utcnow():
        return jsonify({'detail': 'Reset token has expired. Please request a new one.'}), 400
    
    # Update password
    user.set_password(new_password)
    
    # Clear reset token
    user.reset_token = None
    user.reset_token_expiry = None
    
    db.session.commit()
    
    return jsonify({
        'message': 'Password has been reset successfully. You can now login with your new password.'
    }), 200


@bp.route('/verify-reset-token/', methods=['POST'])
def verify_reset_token():
    """Verify if a reset token is valid
    
    Used to check token before showing reset password form.
    """
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    token = request.json.get('token', '').strip()
    
    if not token:
        return jsonify({'valid': False, 'message': 'Token is required.'}), 400
    
    user = User.query.filter_by(reset_token=token).first()
    
    if not user:
        return jsonify({'valid': False, 'message': 'Invalid reset token.'}), 200
    
    if user.reset_token_expiry < datetime.utcnow():
        return jsonify({'valid': False, 'message': 'Reset token has expired.'}), 200
    
    return jsonify({
        'valid': True,
        'email': user.email,
        'username': user.username
    }), 200


