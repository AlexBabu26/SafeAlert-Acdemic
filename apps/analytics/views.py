from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .services import get_summary_stats, get_timeseries_data
from .permissions import IsAdminUser


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def summary_view(request):
    """
    Get summary statistics (counts by status and category).
    """
    stats = get_summary_stats()
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def timeseries_view(request):
    """
    Get time series data (incident volume over time).
    Query parameter: days (default: 30)
    """
    days = int(request.query_params.get('days', 30))
    if days > 365:
        days = 365  # Limit to 1 year
    if days < 1:
        days = 1
    
    data = get_timeseries_data(days=days)
    return Response(data)

