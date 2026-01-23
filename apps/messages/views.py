from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import IncidentMessage
from .serializers import IncidentMessageSerializer, IncidentMessageCreateSerializer
from .permissions import CanViewIncidentMessages, CanSendMessage
from apps.incidents.models import IncidentReport


class IncidentMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for incident messages.
    Users can view messages for their own incidents.
    Admin can view and send messages for all incidents.
    """
    serializer_class = IncidentMessageSerializer
    permission_classes = [IsAuthenticated, CanViewIncidentMessages]

    def get_queryset(self):
        incident_id = self.kwargs.get('incident_id')
        incident = get_object_or_404(IncidentReport, pk=incident_id)
        
        # Admin can see all, users only their own
        if not self.request.user.is_staff and incident.user != self.request.user:
            return IncidentMessage.objects.none()
        
        return IncidentMessage.objects.filter(incident_id=incident_id).select_related('sender')

    def get_serializer_class(self):
        if self.action == 'create':
            return IncidentMessageCreateSerializer
        return IncidentMessageSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [IsAuthenticated, CanSendMessage]
        else:
            self.permission_classes = [IsAuthenticated, CanViewIncidentMessages]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        incident_id = self.kwargs.get('incident_id')
        incident = get_object_or_404(IncidentReport, pk=incident_id)
        
        # Check permission
        if not request.user.is_staff and incident.user != request.user:
            return Response(
                {'detail': 'You do not have permission to send messages to this incident.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

