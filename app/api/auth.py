"""
Authentication API endpoints
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app.models import User
from app.extensions import db
from app.schemas.user import UserRegistrationSchema, UserSchema

bp = Blueprint('auth', __name__)


@bp.route('/register/', methods=['POST'])
def register():
    """User registration endpoint"""
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
    
    # Create user
    user = User(
        username=data['username'],
        email=data.get('email', ''),
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    # Generate JWT tokens (identity will be converted to string by user_identity_loader)
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    user_schema = UserSchema()
    return jsonify({
        'user': user_schema.dump(user),
        'access': access_token,
        'refresh': refresh_token,
    }), 201


@bp.route('/token/', methods=['POST'])
def login():
    """JWT token obtain endpoint (login)"""
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    username = request.json.get('username')
    password = request.json.get('password')
    
    if not username or not password:
        return jsonify({'detail': 'Username and password required.'}), 400
    
    # Find user
    user = User.query.filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        return jsonify({'detail': 'No active account found with the given credentials'}), 401
    
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


