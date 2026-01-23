from django.contrib import admin
from .models import IncidentMessage


@admin.register(IncidentMessage)
class IncidentMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'incident', 'sender', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('message', 'sender__username', 'incident__title')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

