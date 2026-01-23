from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Category, IncidentReport, IncidentAttachment
from .serializers import (
    CategorySerializer, IncidentReportSerializer, IncidentReportCreateSerializer,
    IncidentStatusUpdateSerializer, IncidentAttachmentSerializer
)
from .permissions import IsOwnerOrReadOnly, IsAdminUser
from .filters import IncidentReportFilter


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing categories (read-only for regular users).
    Admin can create/update via admin panel or extend this ViewSet.
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class IncidentReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user incident reports.
    Users can create and view only their own incidents.
    """
    serializer_class = IncidentReportSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = IncidentReportFilter
    search_fields = ['title', 'description', 'location_text']
    ordering_fields = ['created_at', 'updated_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        # Users can only see their own incidents
        return IncidentReport.objects.filter(user=self.request.user).select_related(
            'user', 'category'
        ).prefetch_related('attachments', 'status_history')

    def get_serializer_class(self):
        if self.action == 'create':
            return IncidentReportCreateSerializer
        return IncidentReportSerializer

    def create(self, request, *args, **kwargs):
        """Override create to return full serializer data including id"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return full serializer data with id
        instance = serializer.instance
        response_serializer = IncidentReportSerializer(instance, context={'request': request})
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status='PENDING')

    @action(detail=True, methods=['post'], url_path='attachments')
    def upload_attachment(self, request, pk=None):
        """Upload an attachment file for an incident"""
        incident = self.get_object()
        
        # Check permissions - user must own the incident
        if incident.user != request.user:
            return Response(
                {'detail': 'You do not have permission to upload attachments for this incident.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if 'file' not in request.FILES:
            return Response(
                {'detail': 'No file provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file_obj = request.FILES['file']
        attachment = IncidentAttachment.objects.create(incident=incident, file=file_obj)
        serializer = IncidentAttachmentSerializer(attachment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminIncidentReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin ViewSet for viewing all incidents.
    Admin can update status via the status_update action.
    """
    queryset = IncidentReport.objects.all().select_related('user', 'category').prefetch_related(
        'attachments', 'status_history'
    )
    serializer_class = IncidentReportSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = IncidentReportFilter
    search_fields = ['title', 'description', 'location_text', 'user__username']
    ordering_fields = ['created_at', 'updated_at', 'status']
    ordering = ['-created_at']

    @action(detail=True, methods=['patch'], url_path='status')
    def status_update(self, request, pk=None):
        incident = self.get_object()
        serializer = IncidentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = incident.status
        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')

        # Update status
        incident.status = new_status
        incident.save()

        # Create status history entry
        from .models import StatusHistory
        StatusHistory.objects.create(
            incident=incident,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            notes=notes
        )

        return Response(IncidentReportSerializer(incident).data)

