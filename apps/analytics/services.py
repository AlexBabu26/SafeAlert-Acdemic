from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from apps.incidents.models import IncidentReport, Category


def get_summary_stats():
    """
    Get summary statistics: counts by status and category.
    """
    status_counts = IncidentReport.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    category_counts = IncidentReport.objects.values(
        'category__name', 'category__id'
    ).annotate(
        count=Count('id')
    ).order_by('category__name')
    
    total_incidents = IncidentReport.objects.count()
    pending_count = IncidentReport.objects.filter(status='PENDING').count()
    verified_count = IncidentReport.objects.filter(status='VERIFIED').count()
    resolved_count = IncidentReport.objects.filter(status='RESOLVED').count()
    
    return {
        'total_incidents': total_incidents,
        'status_counts': list(status_counts),
        'category_counts': [
            {'id': item['category__id'], 'name': item['category__name'], 'count': item['count']}
            for item in category_counts
        ],
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
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get daily counts
    daily_counts = IncidentReport.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).extra(
        select={'date': "DATE(created_at)"}
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Fill in missing dates with 0
    date_counts = {}
    for item in daily_counts:
        date_counts[str(item['date'])] = item['count']
    
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

