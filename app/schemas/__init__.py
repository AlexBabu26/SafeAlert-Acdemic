"""
Marshmallow schemas for SafeAlert
"""
from app.schemas.user import UserRegistrationSchema, UserSchema
from app.schemas.incident import (
    CategorySchema,
    CategoryDepartmentMappingSchema,
    IncidentAttachmentSchema,
    IncidentMediaSchema,
    StatusHistorySchema,
    IncidentReportSchema,
    IncidentReportCreateSchema,
    IncidentQuickReportSchema,
    IncidentStatusUpdateSchema,
    IncidentListSchema,
)
from app.schemas.message import IncidentMessageSchema, IncidentMessageCreateSchema
from app.schemas.department import (
    DepartmentSchema,
    DepartmentCreateSchema,
    DepartmentListSchema,
    ResourceSchema,
    ResourceCreateSchema,
)
from app.schemas.assignment import (
    IncidentAssignmentSchema,
    AssignmentStatusUpdateSchema,
    AssignmentListSchema,
    AssignmentDetailSchema,
)
from app.schemas.notification import (
    NotificationSchema,
    NotificationListSchema,
)
from app.schemas.alert import (
    SafetyAlertSchema,
    SafetyAlertCreateSchema,
    SafetyAlertListSchema,
)

__all__ = [
    # User
    'UserRegistrationSchema',
    'UserSchema',
    
    # Incident
    'CategorySchema',
    'CategoryDepartmentMappingSchema',
    'IncidentAttachmentSchema',
    'IncidentMediaSchema',
    'StatusHistorySchema',
    'IncidentReportSchema',
    'IncidentReportCreateSchema',
    'IncidentQuickReportSchema',
    'IncidentStatusUpdateSchema',
    'IncidentListSchema',
    
    # Message
    'IncidentMessageSchema',
    'IncidentMessageCreateSchema',
    
    # Department
    'DepartmentSchema',
    'DepartmentCreateSchema',
    'DepartmentListSchema',
    'ResourceSchema',
    'ResourceCreateSchema',
    
    # Assignment
    'IncidentAssignmentSchema',
    'AssignmentStatusUpdateSchema',
    'AssignmentListSchema',
    'AssignmentDetailSchema',
    
    # Notification
    'NotificationSchema',
    'NotificationListSchema',
    
    # Alert
    'SafetyAlertSchema',
    'SafetyAlertCreateSchema',
    'SafetyAlertListSchema',
]
