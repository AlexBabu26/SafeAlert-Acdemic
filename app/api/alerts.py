"""
Safety Alerts API endpoints
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from app.extensions import db
from app.models import User, SafetyAlert
from app.schemas.alert import SafetyAlertSchema, SafetyAlertListSchema
from app.utils.geo import calculate_distance

bp = Blueprint('alerts', __name__)


@bp.route('/', methods=['GET'])
@jwt_required()
def list_alerts():
    """List active safety alerts"""
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if not user:
        return jsonify({'detail': 'User not found.'}), 404
    
    # Get user's location from request or profile
    user_lat = request.args.get('latitude', type=float)
    user_lng = request.args.get('longitude', type=float)
    
    if not user_lat and user.home_latitude:
        user_lat = float(user.home_latitude)
    if not user_lng and user.home_longitude:
        user_lng = float(user.home_longitude)
    
    # Base query - active alerts
    now = datetime.utcnow()
    query = SafetyAlert.query.filter(
        SafetyAlert.is_active == True,
        SafetyAlert.active_from <= now
    ).filter(
        (SafetyAlert.active_until.is_(None)) | (SafetyAlert.active_until >= now)
    )
    
    alerts = query.order_by(SafetyAlert.created_at.desc()).all()
    
    # Filter by location if provided
    if user_lat and user_lng:
        relevant_alerts = []
        for alert in alerts:
            if alert.is_citywide:
                relevant_alerts.append(alert)
            elif alert.center_lat and alert.center_lng and alert.radius_km:
                distance = calculate_distance(
                    user_lat, user_lng,
                    float(alert.center_lat), float(alert.center_lng)
                )
                if distance <= alert.radius_km:
                    relevant_alerts.append(alert)
            else:
                # No geo restriction
                relevant_alerts.append(alert)
        alerts = relevant_alerts
    
    schema = SafetyAlertListSchema(many=True)
    
    return jsonify({
        'count': len(alerts),
        'results': schema.dump(alerts)
    }), 200


@bp.route('/<int:id>/', methods=['GET'])
@jwt_required()
def get_alert(id):
    """Get alert details"""
    alert = SafetyAlert.query.get(id)
    
    if not alert:
        return jsonify({'detail': 'Not found.'}), 404
    
    schema = SafetyAlertSchema()
    return jsonify(schema.dump(alert)), 200


@bp.route('/active/', methods=['GET'])
def list_active_alerts():
    """List currently active alerts (public endpoint)"""
    now = datetime.utcnow()
    
    alerts = SafetyAlert.query.filter(
        SafetyAlert.is_active == True,
        SafetyAlert.active_from <= now
    ).filter(
        (SafetyAlert.active_until.is_(None)) | (SafetyAlert.active_until >= now)
    ).order_by(SafetyAlert.created_at.desc()).limit(10).all()
    
    schema = SafetyAlertListSchema(many=True)
    
    return jsonify({
        'count': len(alerts),
        'results': schema.dump(alerts)
    }), 200

