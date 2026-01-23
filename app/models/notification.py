"""
Notification model for SafeAlert
"""
from datetime import datetime
from app.extensions import db


class NotificationType:
    """Notification type constants"""
    # Incident-related
    INCIDENT_CREATED = 'INCIDENT_CREATED'
    INCIDENT_ASSIGNED = 'INCIDENT_ASSIGNED'
    INCIDENT_STATUS_CHANGED = 'INCIDENT_STATUS_CHANGED'
    INCIDENT_RESOLVED = 'INCIDENT_RESOLVED'
    
    # Responder-related
    NEW_ASSIGNMENT = 'NEW_ASSIGNMENT'
    ASSIGNMENT_UPDATED = 'ASSIGNMENT_UPDATED'
    ASSIGNMENT_CANCELLED = 'ASSIGNMENT_CANCELLED'
    
    # Communication
    NEW_MESSAGE = 'NEW_MESSAGE'
    
    # Alerts
    SAFETY_ALERT = 'SAFETY_ALERT'
    
    # System
    SYSTEM_ANNOUNCEMENT = 'SYSTEM_ANNOUNCEMENT'
    ESCALATION_TRIGGERED = 'ESCALATION_TRIGGERED'
    
    CHOICES = [
        INCIDENT_CREATED, INCIDENT_ASSIGNED, INCIDENT_STATUS_CHANGED, INCIDENT_RESOLVED,
        NEW_ASSIGNMENT, ASSIGNMENT_UPDATED, ASSIGNMENT_CANCELLED,
        NEW_MESSAGE, SAFETY_ALERT, SYSTEM_ANNOUNCEMENT, ESCALATION_TRIGGERED
    ]


class NotificationPriority:
    """Notification priority levels"""
    LOW = 'LOW'
    NORMAL = 'NORMAL'
    HIGH = 'HIGH'
    URGENT = 'URGENT'
    
    CHOICES = [LOW, NORMAL, HIGH, URGENT]


class Notification(db.Model):
    """In-app notification model"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Content
    type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='NORMAL', nullable=False)
    
    # Related entities (for deep linking)
    data = db.Column(db.JSON, nullable=True)  # {"incident_id": 123, "assignment_id": 456}
    action_url = db.Column(db.String(255), nullable=True)  # URL to navigate to
    
    # Status
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Delivery tracking
    is_pushed = db.Column(db.Boolean, default=False)  # Push notification sent
    pushed_at = db.Column(db.DateTime, nullable=True)
    is_emailed = db.Column(db.Boolean, default=False)  # Email sent
    emailed_at = db.Column(db.DateTime, nullable=True)
    is_sms_sent = db.Column(db.Boolean, default=False)  # SMS sent
    sms_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=True)  # Optional expiration
    
    __table_args__ = (
        db.Index('idx_notification_user_read', 'user_id', 'is_read'),
        db.Index('idx_notification_user_created', 'user_id', 'created_at'),
        db.Index('idx_notification_type', 'type'),
    )
    
    def __repr__(self):
        return f'<Notification {self.id} - {self.type}>'
    
    def mark_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
    
    def mark_pushed(self):
        """Mark push notification as sent"""
        self.is_pushed = True
        self.pushed_at = datetime.utcnow()
    
    def mark_emailed(self):
        """Mark email as sent"""
        self.is_emailed = True
        self.emailed_at = datetime.utcnow()
    
    def mark_sms_sent(self):
        """Mark SMS as sent"""
        self.is_sms_sent = True
        self.sms_sent_at = datetime.utcnow()
    
    @property
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @classmethod
    def create_for_incident(cls, user_id, notification_type, incident, message=None):
        """Create a notification related to an incident"""
        title_map = {
            NotificationType.INCIDENT_CREATED: 'Incident Created',
            NotificationType.INCIDENT_ASSIGNED: 'Incident Assigned',
            NotificationType.INCIDENT_STATUS_CHANGED: 'Status Updated',
            NotificationType.INCIDENT_RESOLVED: 'Incident Resolved',
        }
        
        return cls(
            user_id=user_id,
            type=notification_type,
            title=title_map.get(notification_type, 'Incident Update'),
            message=message or f'Incident #{incident.id} has been updated.',
            data={'incident_id': incident.id},
            action_url=f'/reports/{incident.id}'
        )
    
    @classmethod
    def create_for_assignment(cls, user_id, notification_type, assignment, message=None):
        """Create a notification related to an assignment"""
        title_map = {
            NotificationType.NEW_ASSIGNMENT: 'New Assignment',
            NotificationType.ASSIGNMENT_UPDATED: 'Assignment Updated',
            NotificationType.ASSIGNMENT_CANCELLED: 'Assignment Cancelled',
        }
        
        return cls(
            user_id=user_id,
            type=notification_type,
            title=title_map.get(notification_type, 'Assignment Update'),
            message=message or f'Assignment #{assignment.id} has been updated.',
            priority=NotificationPriority.HIGH if notification_type == NotificationType.NEW_ASSIGNMENT else NotificationPriority.NORMAL,
            data={'assignment_id': assignment.id, 'incident_id': assignment.incident_id},
            action_url=f'/responder/assignments/{assignment.id}'
        )

