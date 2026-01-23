"""
SQLAlchemy models for SafeAlert
"""
from app.models.user import User
from app.models.incident import (
    Category, 
    CategoryDepartmentMapping,
    IncidentReport, 
    IncidentAttachment, 
    IncidentMedia,
    StatusHistory,
    IncidentStatus,
    IncidentSeverity,
)
from app.models.message import IncidentMessage
from app.models.department import (
    Department, 
    Resource,
    DepartmentType,
    ResourceType,
    ResourceStatus,
)
from app.models.assignment import (
    IncidentAssignment,
    AssignmentStatus,
)
from app.models.notification import (
    Notification,
    NotificationType,
    NotificationPriority,
)
from app.models.escalation import (
    EscalationRule,
    EscalationLog,
    EscalationTrigger,
    EscalationAction,
)
from app.models.alert import (
    SafetyAlert,
    AlertSeverity,
    AlertType,
)

__all__ = [
    # User
    'User',
    
    # Incident
    'Category',
    'CategoryDepartmentMapping',
    'IncidentReport',
    'IncidentAttachment',
    'IncidentMedia',
    'StatusHistory',
    'IncidentStatus',
    'IncidentSeverity',
    
    # Message
    'IncidentMessage',
    
    # Department
    'Department',
    'Resource',
    'DepartmentType',
    'ResourceType',
    'ResourceStatus',
    
    # Assignment
    'IncidentAssignment',
    'AssignmentStatus',
    
    # Notification
    'Notification',
    'NotificationType',
    'NotificationPriority',
    
    # Escalation
    'EscalationRule',
    'EscalationLog',
    'EscalationTrigger',
    'EscalationAction',
    
    # Alert
    'SafetyAlert',
    'AlertSeverity',
    'AlertType',
]
