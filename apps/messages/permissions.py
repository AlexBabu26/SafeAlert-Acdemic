from rest_framework import permissions
from apps.incidents.models import IncidentReport


class CanViewIncidentMessages(permissions.BasePermission):
    """
    Permission to view messages: user can view messages for their own incidents,
    admin can view messages for all incidents.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        incident_id = view.kwargs.get('incident_id')
        if not incident_id:
            return False
        
        try:
            incident = IncidentReport.objects.get(pk=incident_id)
        except IncidentReport.DoesNotExist:
            return False
        
        # Admin can view all, user can view only their own
        return request.user.is_staff or incident.user == request.user


class CanSendMessage(permissions.BasePermission):
    """
    Permission to send messages: admin can send to any incident,
    users can send to their own incidents (optional, can be disabled).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        incident_id = view.kwargs.get('incident_id')
        if not incident_id:
            return False
        
        try:
            incident = IncidentReport.objects.get(pk=incident_id)
        except IncidentReport.DoesNotExist:
            return False
        
        # Admin can always send
        if request.user.is_staff:
            return True
        
        # Users can send to their own incidents (optional feature)
        return incident.user == request.user

