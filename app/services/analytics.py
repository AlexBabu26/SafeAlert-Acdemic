"""
Analytics services for SafeAlert
"""
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from app.models import IncidentReport, Category
from app.extensions import db


def get_summary_stats():
    """
    Get summary statistics: counts by status and category.
    """
    # Status counts
    status_counts = db.session.query(
        IncidentReport.status,
        func.count(IncidentReport.id).label('count')
    ).group_by(IncidentReport.status).order_by(IncidentReport.status).all()
    
    status_counts_list = [{'status': status, 'count': count} for status, count in status_counts]
    
    # Category counts
    category_counts = db.session.query(
        Category.id.label('category__id'),
        Category.name.label('category__name'),
        func.count(IncidentReport.id).label('count')
    ).join(IncidentReport, Category.id == IncidentReport.category_id)\
     .group_by(Category.id, Category.name)\
     .order_by(Category.name).all()
    
    category_counts_list = [
        {
            'id': item.category__id,
            'name': item.category__name,
            'count': item.count
        }
        for item in category_counts
    ]
    
    # Summary counts
    total_incidents = IncidentReport.query.count()
    pending_count = IncidentReport.query.filter_by(status='PENDING').count()
    verified_count = IncidentReport.query.filter_by(status='VERIFIED').count()
    resolved_count = IncidentReport.query.filter_by(status='RESOLVED').count()
    
    return {
        'total_incidents': total_incidents,
        'status_counts': status_counts_list,
        'category_counts': category_counts_list,
        'summary': {
            'pending': pending_count,
            'verified': verified_count,
            'resolved': resolved_count,
        }
    }


def get_timeseries_data(days=30):
    """
    Get incident volume over time (daily counts for the last N days).
    """
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    # Get daily counts using SQLAlchemy
    # For SQLite, we use DATE() function
    daily_counts_query = db.session.query(
        func.date(IncidentReport.created_at).label('date'),
        func.count(IncidentReport.id).label('count')
    ).filter(
        and_(
            func.date(IncidentReport.created_at) >= start_date,
            func.date(IncidentReport.created_at) <= end_date
        )
    ).group_by(func.date(IncidentReport.created_at))\
     .order_by(func.date(IncidentReport.created_at)).all()
    
    # Create date counts dictionary
    date_counts = {}
    for item in daily_counts_query:
        date_str = str(item.date)
        date_counts[date_str] = item.count
    
    # Fill in missing dates with 0
    result = []
    current_date = start_date
    while current_date <= end_date:
        date_str = str(current_date)
        result.append({
            'date': date_str,
            'count': date_counts.get(date_str, 0)
        })
        current_date += timedelta(days=1)
    
    return {
        'days': days,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'data': result
    }


