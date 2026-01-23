"""
Admin incidents API endpoints
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.models import User, IncidentReport, StatusHistory, Category
from app.extensions import db
from app.schemas.incident import IncidentReportSchema, IncidentStatusUpdateSchema
from app.utils.permissions import admin_required
from app.utils.filters import apply_incident_filters, apply_ordering, paginate_query

bp = Blueprint('admin_incidents', __name__)


@bp.route('/incidents/', methods=['GET'])
@admin_required
def list_all_incidents():
    """List all incidents (admin only)"""
    # Start with all incidents
    query = IncidentReport.query
    
    # Apply filters
    query = apply_incident_filters(
        query,
        status=request.args.get('status'),
        category=request.args.get('category', type=int),
        created_after=request.args.get('created_after'),
        created_before=request.args.get('created_before'),
        search=request.args.get('search')
    )
    
    # Apply ordering
    ordering = request.args.get('ordering', '-created_at')
    query = apply_ordering(query, ordering)
    
    # Pagination
    from flask import current_app
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('PAGINATION_PER_PAGE', 20)
    
    paginated_query, total = paginate_query(query, page, per_page)
    incidents = paginated_query.all()
    
    schema = IncidentReportSchema(many=True)
    results = schema.dump(incidents)
    
    return jsonify({
        'count': total,
        'next': f'/api/admin/incidents/?page={page + 1}' if page * per_page < total else None,
        'previous': f'/api/admin/incidents/?page={page - 1}' if page > 1 else None,
        'results': results
    }), 200


@bp.route('/incidents/<int:id>/', methods=['GET'])
@admin_required
def get_incident(id):
    """Get incident details (admin only)"""
    incident = IncidentReport.query.get(id)
    
    if not incident:
        return jsonify({'detail': 'Not found.'}), 404
    
    schema = IncidentReportSchema()
    return jsonify(schema.dump(incident)), 200


@bp.route('/incidents/<int:id>/status/', methods=['PATCH'])
@admin_required
def update_status(id):
    """Update incident status (admin only)"""
    if not request.is_json:
        return jsonify({'detail': 'JSON data required.'}), 400
    
    incident = IncidentReport.query.get(id)
    
    if not incident:
        return jsonify({'detail': 'Not found.'}), 404
    
    schema = IncidentStatusUpdateSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    current_user_id = get_jwt_identity()  # Returns string from JWT
    user = User.query.get(int(current_user_id))
    
    old_status = incident.status
    new_status = data['status']
    notes = data.get('notes', '')
    
    # Update status
    incident.status = new_status
    db.session.commit()
    
    # Create status history entry
    status_history = StatusHistory(
        incident_id=incident.id,
        old_status=old_status,
        new_status=new_status,
        changed_by_id=user.id,
        notes=notes
    )
    
    db.session.add(status_history)
    db.session.commit()
    
    # Return updated incident
    response_schema = IncidentReportSchema()
    return jsonify(response_schema.dump(incident)), 200

