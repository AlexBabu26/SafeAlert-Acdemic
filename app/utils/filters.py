"""
Filtering utilities for querying incidents
"""
from datetime import datetime
from sqlalchemy import or_, and_
from app.models import IncidentReport, Category


def apply_incident_filters(query, status=None, category=None, created_after=None, 
                          created_before=None, search=None, user_id=None):
    """
    Apply filters to incident query
    
    Args:
        query: SQLAlchemy query object
        status: Filter by status (PENDING, VERIFIED, RESOLVED)
        category: Filter by category ID
        created_after: Filter incidents created after this datetime
        created_before: Filter incidents created before this datetime
        search: Search in title, description, location_text
        user_id: Filter by user ID (for user-specific queries)
    
    Returns:
        Filtered query
    """
    if user_id is not None:
        query = query.filter(IncidentReport.user_id == user_id)
    
    if status:
        query = query.filter(IncidentReport.status == status)
    
    if category:
        query = query.filter(IncidentReport.category_id == category)
    
    if created_after:
        if isinstance(created_after, str):
            created_after = datetime.fromisoformat(created_after.replace('Z', '+00:00'))
        query = query.filter(IncidentReport.created_at >= created_after)
    
    if created_before:
        if isinstance(created_before, str):
            created_before = datetime.fromisoformat(created_before.replace('Z', '+00:00'))
        query = query.filter(IncidentReport.created_at <= created_before)
    
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            or_(
                IncidentReport.title.ilike(search_pattern),
                IncidentReport.description.ilike(search_pattern),
                IncidentReport.location_text.ilike(search_pattern)
            )
        )
    
    return query


def apply_ordering(query, ordering=None):
    """
    Apply ordering to query
    
    Args:
        query: SQLAlchemy query object
        ordering: Ordering field (e.g., 'created_at', '-created_at', 'status')
    
    Returns:
        Ordered query
    """
    if not ordering:
        return query.order_by(IncidentReport.created_at.desc())
    
    # Handle multiple ordering fields (comma-separated)
    order_fields = []
    for field in ordering.split(','):
        field = field.strip()
        if field.startswith('-'):
            # Descending order
            field_name = field[1:]
            if hasattr(IncidentReport, field_name):
                order_fields.append(getattr(IncidentReport, field_name).desc())
        else:
            # Ascending order
            if hasattr(IncidentReport, field):
                order_fields.append(getattr(IncidentReport, field))
    
    if order_fields:
        return query.order_by(*order_fields)
    
    return query.order_by(IncidentReport.created_at.desc())


def paginate_query(query, page=1, per_page=20):
    """
    Paginate query results
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        per_page: Items per page
    
    Returns:
        Tuple of (paginated_query, total_count)
    """
    total = query.count()
    paginated_query = query.offset((page - 1) * per_page).limit(per_page)
    return paginated_query, total

