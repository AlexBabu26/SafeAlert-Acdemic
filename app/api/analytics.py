"""
Analytics API endpoints
"""
from flask import Blueprint, request, jsonify

from app.services.analytics import get_summary_stats, get_timeseries_data
from app.services.department_analytics import (
    get_department_summary_stats,
    get_department_timeseries_data
)
from app.utils.permissions import admin_required, department_required

bp = Blueprint('analytics', __name__)


# Admin analytics endpoints (all data)
@bp.route('/summary/', methods=['GET'])
@admin_required
def summary(user):
    """Get summary statistics (admin only - all data)"""
    stats = get_summary_stats()
    return jsonify(stats), 200


@bp.route('/timeseries/', methods=['GET'])
@admin_required
def timeseries(user):
    """Get time series data (admin only - all data)"""
    days = request.args.get('days', 30, type=int)
    
    # Limit to 1 year
    if days > 365:
        days = 365
    if days < 1:
        days = 1
    
    data = get_timeseries_data(days=days)
    return jsonify(data), 200




