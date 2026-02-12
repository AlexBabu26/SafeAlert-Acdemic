"""
Incidents API endpoints for users
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from werkzeug.utils import secure_filename
from marshmallow import ValidationError
from pathlib import Path
from datetime import datetime
import os

from app.models import User, IncidentReport, IncidentAttachment, IncidentMedia, Category
from app.extensions import db
from app.schemas.incident import (
    IncidentReportSchema, 
    IncidentReportCreateSchema, 
    IncidentQuickReportSchema,
    IncidentAttachmentSchema,
    IncidentMediaSchema,
)
from app.utils.permissions import owner_required
from app.utils.filters import apply_incident_filters, apply_ordering, paginate_query
from app.services.notification import NotificationService
from app.socketio_events import broadcast_incident_created

bp = Blueprint('incidents', __name__)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def get_media_type(filename):
    """Determine media type from filename"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    image_exts = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'}
    video_exts = {'mp4', 'mov', 'avi', 'webm', 'mkv'}
    audio_exts = {'mp3', 'wav', 'ogg', 'm4a', 'webm'}
    doc_exts = {'pdf', 'doc', 'docx', 'txt'}
    
    if ext in image_exts:
        return 'IMAGE'
    elif ext in video_exts:
        return 'VIDEO'
    elif ext in audio_exts:
        return 'AUDIO'
    elif ext in doc_exts:
        return 'DOCUMENT'
    return 'OTHER'


@bp.route('/', methods=['POST'])
@jwt_required()
def create_incident():
    """Create a new incident report"""
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if not user:
        return jsonify({'detail': 'User not found.'}), 404
    
    schema = IncidentReportCreateSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    # Get category_id from data
    category_id = data.get('category')
    if not category_id:
        return jsonify({'category': ['Category is required.']}), 400
    
    # Verify category exists and is active
    category = Category.query.get(category_id)
    if not category or not category.is_active:
        return jsonify({'category': ['Invalid category.']}), 400
    
    # Check if anonymous
    is_anonymous = data.get('is_anonymous', False)
    
    # Create incident
    incident = IncidentReport(
        user_id=None if is_anonymous else user.id,
        is_anonymous=is_anonymous,
        category_id=category_id,
        severity=data.get('severity', category.default_severity or 'MEDIUM'),
        title=data.get('title', ''),
        description=data['description'],
        location_text=data.get('location_text', ''),
        address_formatted=data.get('address_formatted'),
        landmark_description=data.get('landmark_description'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        estimated_affected_people=data.get('estimated_affected_people'),
        requires_evacuation=data.get('requires_evacuation', False),
        status='REPORTED',
        source='WEB',
        ip_address=request.remote_addr,
    )
    
    # Generate tracking code for ALL reports (not just anonymous)
    from app.models.incident import generate_tracking_code
    incident.anonymous_tracking_code = generate_tracking_code()
    
    db.session.add(incident)
    db.session.commit()
    
    # Broadcast to dispatchers
    broadcast_incident_created(incident)
    
    # Notify dispatchers
    notification_service = NotificationService()
    notification_service.notify_incident_created(incident)
    
    # Return full incident data
    response_schema = IncidentReportSchema()
    response_data = response_schema.dump(incident)
    
    # Always include tracking code (for both anonymous and authenticated users)
    response_data['tracking_code'] = incident.anonymous_tracking_code
    if is_anonymous:
        response_data['message'] = 'Your anonymous report has been submitted. Save your tracking code to check status later.'
    else:
        response_data['message'] = 'Your report has been submitted successfully. You can track it using the tracking code or from your dashboard.'
    
    return jsonify(response_data), 201


@bp.route('/quick/', methods=['POST'])
def quick_report():
    """Create a quick/panic emergency report with minimal data.

    This endpoint supports both authenticated and unauthenticated requests.
    """
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400

    # Optional authentication: if JWT exists and is valid, link report to user.
    verify_jwt_in_request(optional=True)
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id)) if current_user_id else None
    
    schema = IncidentQuickReportSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    # Get category (default to first "Emergency" category if not specified)
    category_id = data.get('category')
    if not category_id:
        category = Category.query.filter(
            Category.name.ilike('%emergency%'),
            Category.is_active == True
        ).first()
        if not category:
            category = Category.query.filter(Category.is_active == True).first()
        category_id = category.id if category else None
    
    if not category_id:
        return jsonify({'detail': 'No categories available.'}), 400
    
    # Create quick incident
    from app.models.incident import generate_tracking_code
    
    incident = IncidentReport(
        user_id=user.id if user else None,
        is_anonymous=(user is None),
        category_id=category_id,
        severity=data.get('severity', 'CRITICAL'),
        title='Quick Emergency Report',
        description=data.get('description', 'Emergency assistance requested'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        anonymous_tracking_code=generate_tracking_code(),
        status='REPORTED',
        source='QUICK',
        ip_address=request.remote_addr,
    )
    
    db.session.add(incident)
    db.session.commit()
    
    # Broadcast to dispatchers
    broadcast_incident_created(incident)
    
    # Notify dispatchers with high priority
    notification_service = NotificationService()
    notification_service.notify_incident_created(incident)
    
    response_schema = IncidentReportSchema()
    return jsonify({
        'message': 'Emergency report submitted. Help is on the way.',
        'tracking_code': incident.anonymous_tracking_code,
        'incident': response_schema.dump(incident)
    }), 201


@bp.route('/anonymous/', methods=['POST'])
def create_anonymous_incident():
    """Create an anonymous incident report (no authentication required)"""
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    schema = IncidentReportCreateSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    # Get category_id from data
    category_id = data.get('category')
    if not category_id:
        return jsonify({'category': ['Category is required.']}), 400
    
    # Verify category exists and is active
    category = Category.query.get(category_id)
    if not category or not category.is_active:
        return jsonify({'category': ['Invalid category.']}), 400
    
    # Create anonymous incident
    from app.models.incident import generate_tracking_code
    
    incident = IncidentReport(
        user_id=None,
        is_anonymous=True,
        anonymous_tracking_code=generate_tracking_code(),
        category_id=category_id,
        severity=data.get('severity', category.default_severity or 'MEDIUM'),
        title=data.get('title', ''),
        description=data['description'],
        location_text=data.get('location_text', ''),
        address_formatted=data.get('address_formatted'),
        landmark_description=data.get('landmark_description'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        estimated_affected_people=data.get('estimated_affected_people'),
        requires_evacuation=data.get('requires_evacuation', False),
        status='REPORTED',
        source='WEB',
        ip_address=request.remote_addr,
    )
    
    db.session.add(incident)
    db.session.commit()
    
    # Broadcast to dispatchers
    broadcast_incident_created(incident)
    
    # Notify dispatchers
    notification_service = NotificationService()
    notification_service.notify_incident_created(incident)
    
    return jsonify({
        'message': 'Your anonymous report has been submitted.',
        'tracking_code': incident.anonymous_tracking_code,
        'note': 'Save this tracking code to check the status of your report.'
    }), 201


@bp.route('/track/<tracking_code>/', methods=['GET'])
def track_anonymous_report(tracking_code):
    """Track a report by tracking code (anonymous or authenticated)."""
    normalized_code = (tracking_code or '').strip().upper()
    if not normalized_code:
        return jsonify({'detail': 'Tracking code is required.'}), 400

    # Tracking codes are generated in uppercase; normalize user input to match.
    incident = IncidentReport.query.filter_by(
        anonymous_tracking_code=normalized_code
    ).first()
    
    if not incident:
        return jsonify({'detail': 'Report not found.'}), 404
    
    # Return limited public tracking info.
    return jsonify({
        'tracking_code': incident.anonymous_tracking_code,
        'status': incident.status,
        'severity': incident.severity,
        'category': incident.category.name if incident.category else None,
        'created_at': incident.created_at.isoformat(),
        'updated_at': incident.updated_at.isoformat(),
        'is_active': incident.is_active,
    }), 200


@bp.route('/', methods=['GET'])
@jwt_required()
def list_incidents():
    """List user's incidents with filtering and pagination"""
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if not user:
        return jsonify({'detail': 'User not found.'}), 404
    
    # Start with user's incidents
    query = IncidentReport.query.filter_by(user_id=user.id)
    
    # Apply filters
    query = apply_incident_filters(
        query,
        status=request.args.get('status'),
        category=request.args.get('category', type=int),
        created_after=request.args.get('created_after'),
        created_before=request.args.get('created_before'),
        search=request.args.get('search'),
        user_id=user.id
    )
    
    # Apply ordering
    ordering = request.args.get('ordering', '-created_at')
    query = apply_ordering(query, ordering)
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('PAGINATION_PER_PAGE', 20)
    
    paginated_query, total = paginate_query(query, page, per_page)
    incidents = paginated_query.all()
    
    schema = IncidentReportSchema(many=True)
    results = schema.dump(incidents)
    
    return jsonify({
        'count': total,
        'next': f'/api/incidents/?page={page + 1}' if page * per_page < total else None,
        'previous': f'/api/incidents/?page={page - 1}' if page > 1 else None,
        'results': results
    }), 200


@bp.route('/<int:id>/', methods=['GET'])
@owner_required
def get_incident(user, id):
    """Get incident details"""
    incident = IncidentReport.query.get(id)
    
    if not incident:
        return jsonify({'detail': 'Not found.'}), 404
    
    schema = IncidentReportSchema()
    result = schema.dump(incident)
    
    # Include assignments for the user to see who is responding
    if incident.assignments.count() > 0:
        result['responders'] = [{
            'department_name': a.department.name if a.department else None,
            'status': a.status,
            'assigned_at': a.assigned_at.isoformat() if a.assigned_at else None,
        } for a in incident.assignments.filter(
            IncidentAssignment.status.in_(['ACCEPTED', 'EN_ROUTE', 'ON_SCENE'])
        )]
    
    return jsonify(result), 200


@bp.route('/<int:id>/attachments/', methods=['POST'])
@owner_required
def upload_attachment(user, id):
    """Upload an attachment file for an incident"""
    incident = IncidentReport.query.get(id)
    
    if not incident:
        return jsonify({'detail': 'Not found.'}), 404
    
    # Check permissions - user must own the incident
    if not user.is_staff and incident.user_id != user.id:
        return jsonify({'detail': 'You do not have permission to upload attachments for this incident.'}), 403
    
    if 'file' not in request.files:
        return jsonify({'detail': 'No file provided.'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'detail': 'No file selected.'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'detail': 'File type not allowed.'}), 400
    
    # Create upload directory structure: incidents/YYYY/MM/DD/
    now = datetime.utcnow()
    upload_dir = Path(current_app.config['UPLOAD_FOLDER']) / 'incidents' / \
                 str(now.year) / f'{now.month:02d}' / f'{now.day:02d}'
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    filename = secure_filename(file.filename)
    file_path = upload_dir / filename
    
    # Handle duplicate filenames
    counter = 1
    original_filename = filename
    while file_path.exists():
        name, ext = os.path.splitext(original_filename)
        filename = f'{name}_{counter}{ext}'
        file_path = upload_dir / filename
        counter += 1
    
    file.save(str(file_path))
    
    # Get file size
    file_size = os.path.getsize(str(file_path))
    
    # Determine media type
    media_type = get_media_type(filename)
    
    # Create attachment record (store relative path with forward slashes for URLs)
    relative_path = file_path.relative_to(current_app.config['UPLOAD_FOLDER']).as_posix()
    
    # Create both legacy attachment and new media record
    attachment = IncidentAttachment(
        incident_id=incident.id,
        file_path=relative_path
    )
    
    media = IncidentMedia(
        incident_id=incident.id,
        file_path=relative_path,
        media_type=media_type,
        file_size_bytes=file_size,
    )
    
    db.session.add(attachment)
    db.session.add(media)
    db.session.commit()
    
    schema = IncidentMediaSchema()
    return jsonify(schema.dump(media)), 201


# Import for responder info in get_incident
from app.models import IncidentAssignment
