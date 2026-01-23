"""
Notifications API endpoints
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import User, Notification
from app.schemas.notification import NotificationSchema, NotificationListSchema

bp = Blueprint('notifications', __name__)


@bp.route('/', methods=['GET'])
@jwt_required()
def list_notifications():
    """List user's notifications"""
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if not user:
        return jsonify({'detail': 'User not found.'}), 404
    
    # Filter parameters
    is_read = request.args.get('is_read')
    notification_type = request.args.get('type')
    
    # Base query
    query = Notification.query.filter(Notification.user_id == user.id)
    
    # Apply filters
    if is_read is not None:
        query = query.filter(Notification.is_read == (is_read.lower() == 'true'))
    
    if notification_type:
        query = query.filter(Notification.type == notification_type)
    
    # Order by created_at descending
    query = query.order_by(Notification.created_at.desc())
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('PAGINATION_PER_PAGE', 20)
    
    total = query.count()
    notifications = query.offset((page - 1) * per_page).limit(per_page).all()
    
    schema = NotificationListSchema(many=True)
    
    return jsonify({
        'count': total,
        'unread_count': Notification.query.filter(
            Notification.user_id == user.id,
            Notification.is_read == False
        ).count(),
        'next': f'/api/notifications/?page={page + 1}' if page * per_page < total else None,
        'previous': f'/api/notifications/?page={page - 1}' if page > 1 else None,
        'results': schema.dump(notifications)
    }), 200


@bp.route('/<int:id>/', methods=['GET'])
@jwt_required()
def get_notification(id):
    """Get notification details"""
    current_user_id = get_jwt_identity()
    
    notification = Notification.query.filter_by(
        id=id,
        user_id=int(current_user_id)
    ).first()
    
    if not notification:
        return jsonify({'detail': 'Not found.'}), 404
    
    schema = NotificationSchema()
    return jsonify(schema.dump(notification)), 200


@bp.route('/<int:id>/read/', methods=['POST'])
@jwt_required()
def mark_read(id):
    """Mark notification as read"""
    current_user_id = get_jwt_identity()
    
    notification = Notification.query.filter_by(
        id=id,
        user_id=int(current_user_id)
    ).first()
    
    if not notification:
        return jsonify({'detail': 'Not found.'}), 404
    
    notification.mark_read()
    db.session.commit()
    
    return jsonify({'status': 'ok', 'is_read': True}), 200


@bp.route('/read-all/', methods=['POST'])
@jwt_required()
def mark_all_read():
    """Mark all notifications as read"""
    current_user_id = get_jwt_identity()
    
    from app.services.notification import NotificationService
    notification_service = NotificationService()
    count = notification_service.mark_all_read(int(current_user_id))
    
    return jsonify({
        'status': 'ok',
        'marked_read': count
    }), 200


@bp.route('/unread-count/', methods=['GET'])
@jwt_required()
def get_unread_count():
    """Get count of unread notifications"""
    current_user_id = get_jwt_identity()
    
    count = Notification.query.filter(
        Notification.user_id == int(current_user_id),
        Notification.is_read == False
    ).count()
    
    return jsonify({'unread_count': count}), 200

