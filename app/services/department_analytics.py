"""
Department-specific analytics services
"""
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from app.models import (
    IncidentReport, 
    Category, 
    IncidentAssignment,
    AssignmentStatus,
    Department
)
from app.extensions import db


def get_department_summary_stats(department_id):
    """
    Get summary statistics for department's assigned incidents.
    """
    # Status counts for department's incidents
    status_counts = db.session.query(
        IncidentReport.status,
        func.count(func.distinct(IncidentReport.id)).label('count')
    ).join(
        IncidentAssignment,
        IncidentAssignment.incident_id == IncidentReport.id
    ).filter(
        IncidentAssignment.department_id == department_id
    ).group_by(IncidentReport.status).order_by(IncidentReport.status).all()
    
    status_counts_list = [{'status': str(status), 'count': count} for status, count in status_counts]
    
    # Category counts for department's incidents
    category_counts = db.session.query(
        Category.id.label('category__id'),
        Category.name.label('category__name'),
        func.count(func.distinct(IncidentReport.id)).label('count')
    ).join(IncidentReport, Category.id == IncidentReport.category_id)\
     .join(IncidentAssignment, IncidentAssignment.incident_id == IncidentReport.id)\
     .filter(IncidentAssignment.department_id == department_id)\
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
    
    # Assignment stats for department
    total_assignments = IncidentAssignment.query.filter_by(
        department_id=department_id
    ).count()
    
    active_assignments = IncidentAssignment.query.filter(
        IncidentAssignment.department_id == department_id,
        IncidentAssignment.status.in_(AssignmentStatus.ACTIVE_STATUSES)
    ).count()
    
    completed_assignments = IncidentAssignment.query.filter(
        IncidentAssignment.department_id == department_id,
        IncidentAssignment.status == AssignmentStatus.COMPLETED
    ).count()
    
    # Average response time for department
    avg_response_time = db.session.query(
        func.avg(IncidentAssignment.total_response_time_seconds)
    ).filter(
        IncidentAssignment.department_id == department_id,
        IncidentAssignment.status == AssignmentStatus.COMPLETED,
        IncidentAssignment.total_response_time_seconds.isnot(None)
    ).scalar()
    
    # Summary counts
    total_incidents = db.session.query(func.count(func.distinct(IncidentReport.id)))\
        .join(IncidentAssignment, IncidentAssignment.incident_id == IncidentReport.id)\
        .filter(IncidentAssignment.department_id == department_id)\
        .scalar() or 0
    
    pending_count = db.session.query(func.count(func.distinct(IncidentReport.id)))\
        .join(IncidentAssignment, IncidentAssignment.incident_id == IncidentReport.id)\
        .filter(
            IncidentAssignment.department_id == department_id,
            IncidentReport.status == 'PENDING'
        ).scalar() or 0
    
    resolved_count = db.session.query(func.count(func.distinct(IncidentReport.id)))\
        .join(IncidentAssignment, IncidentAssignment.incident_id == IncidentReport.id)\
        .filter(
            IncidentAssignment.department_id == department_id,
            IncidentReport.status == 'RESOLVED'
        ).scalar() or 0
    
    # Get department info
    department = Department.query.get(department_id)
    department_name = department.name if department else f"Department #{department_id}"
    
    return {
        'department_id': department_id,
        'department_name': department_name,
        'total_incidents': total_incidents,
        'status_counts': status_counts_list,
        'category_counts': category_counts_list,
        'assignments': {
            'total': total_assignments,
            'active': active_assignments,
            'completed': completed_assignments,
            'avg_response_time_seconds': float(avg_response_time) if avg_response_time else None
        },
        'summary': {
            'pending': pending_count,
            'resolved': resolved_count,
        }
    }


def get_department_timeseries_data(department_id, days=30):
    """
    Get incident volume over time for department.
    """
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    # Get daily counts for department's incidents
    daily_counts_query = db.session.query(
        func.date(IncidentReport.created_at).label('date'),
        func.count(func.distinct(IncidentReport.id)).label('count')
    ).join(
        IncidentAssignment,
        IncidentAssignment.incident_id == IncidentReport.id
    ).filter(
        and_(
            IncidentAssignment.department_id == department_id,
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
    
    # Get department info
    department = Department.query.get(department_id)
    department_name = department.name if department else f"Department #{department_id}"
    
    return {
        'department_id': department_id,
        'department_name': department_name,
        'days': days,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'data': result
    }

