"""
Messages API endpoints
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.models import User, IncidentReport, IncidentMessage
from app.extensions import db
from app.schemas.message import IncidentMessageSchema, IncidentMessageCreateSchema
from app.utils.permissions import can_view_incident_messages, can_send_message

bp = Blueprint('messages', __name__, url_prefix='/api/incidents')


@bp.route('/<int:incident_id>/messages/', methods=['GET'])
@jwt_required()
def list_messages(incident_id):
    """List messages for an incident"""
    current_user_id = get_jwt_identity()  # Returns string from JWT
    user = User.query.get(int(current_user_id))
    
    # Check permissions
    can_view, error_response, status_code = can_view_incident_messages(incident_id, user)
    if not can_view:
        return error_response, status_code
    
    # Get messages
    messages = IncidentMessage.query.filter_by(incident_id=incident_id).order_by(IncidentMessage.created_at).all()
    
    schema = IncidentMessageSchema(many=True)
    return jsonify(schema.dump(messages)), 200


@bp.route('/<int:incident_id>/messages/', methods=['POST'])
@jwt_required()
def create_message(incident_id):
    """Create a message for an incident"""
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    current_user_id = get_jwt_identity()  # Returns string from JWT
    user = User.query.get(int(current_user_id))
    
    if not user:
        return jsonify({'detail': 'User not found.'}), 404
    
    # Check permissions
    can_send, error_response, status_code = can_send_message(incident_id, user)
    if not can_send:
        return error_response, status_code
    
    schema = IncidentMessageCreateSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    # Create message
    message = IncidentMessage(
        incident_id=incident_id,
        sender_id=user.id,
        message=data['message']
    )
    
    db.session.add(message)
    db.session.commit()
    
    response_schema = IncidentMessageSchema()
    return jsonify(response_schema.dump(message)), 201

