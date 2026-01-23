import django_filters
from .models import IncidentReport, Category


class IncidentReportFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=IncidentReport._meta.get_field('status').choices)
    category = django_filters.ModelChoiceFilter(queryset=Category.objects.filter(is_active=True))
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    search = django_filters.CharFilter(field_name='description', lookup_expr='icontains')

    class Meta:
        model = IncidentReport
        fields = ['status', 'category', 'created_after', 'created_before', 'search']

