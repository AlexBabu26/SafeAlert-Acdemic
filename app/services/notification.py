"""
Notification Service for SafeAlert

Handles multi-channel notifications to users.
"""
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.extensions import db
from app.models import (
    User,
    Notification,
    NotificationType,
    NotificationPriority,
    IncidentReport,
    IncidentAssignment,
)


class NotificationService:
    """
    Service for sending notifications through multiple channels.
    
    Supports:
    - In-app notifications (always)
    - WebSocket real-time updates
    - Push notifications (if push_token available)
    - SMS (for critical notifications)
    - Email (for non-urgent updates)
    """
    
    def __init__(self, socketio=None):
        """
        Initialize notification service.
        
        Args:
            socketio: Optional Flask-SocketIO instance for real-time updates
        """
        self.socketio = socketio
    
    def notify_user(
        self,
        user: User,
        notification_type: str,
        message: str,
        title: str = None,
        priority: str = NotificationPriority.NORMAL,
        data: Dict[str, Any] = None,
        action_url: str = None,
        send_push: bool = True,
        send_email: bool = False,
        send_sms: bool = False
    ) -> Notification:
        """
        Send a notification to a user.
        
        Args:
            user: User to notify
            notification_type: Type of notification
            message: Notification message
            title: Optional title (auto-generated if not provided)
            priority: Notification priority level
            data: Additional data payload
            action_url: URL to navigate to when clicked
            send_push: Whether to send push notification
            send_email: Whether to send email
            send_sms: Whether to send SMS
        
        Returns:
            Created Notification object
        """
        # Auto-generate title if not provided
        if not title:
            title = self._get_default_title(notification_type)
        
        # Create in-app notification
        notification = Notification(
            user_id=user.id,
            type=notification_type,
            title=title,
            message=message,
            priority=priority,
            data=data,
            action_url=action_url
        )
        
        db.session.add(notification)
        db.session.commit()
        
        # Send via WebSocket if available
        if self.socketio:
            self._send_websocket(user.id, notification)
        
        # Send push notification
        if send_push and user.push_token:
            self._send_push_notification(user, notification)
        
        # Send email for non-urgent notifications
        if send_email and user.email:
            self._send_email(user, notification)
        
        # Send SMS for critical notifications
        if send_sms and user.phone_number:
            self._send_sms(user, notification)
        
        return notification
    
    def notify_incident_created(self, incident: IncidentReport) -> List[Notification]:
        """
        Notify relevant parties about a new incident.
        
        Args:
            incident: The newly created incident
        
        Returns:
            List of created notifications
        """
        notifications = []
        
        # Notify departments
        departments = User.query.filter(User.is_department == True).all()
        
        for dispatcher in departments:
            notification = self.notify_user(
                dispatcher,
                NotificationType.INCIDENT_CREATED,
                f'New {incident.severity} incident reported: {incident.title or "No title"}',
                priority=self._severity_to_priority(incident.severity),
                data={'incident_id': incident.id},
                action_url=f'/dispatcher/incidents/{incident.id}'
            )
            notifications.append(notification)
        
        return notifications
    
    def notify_assignment_created(self, assignment: IncidentAssignment) -> List[Notification]:
        """
        Notify responders about a new assignment.
        
        Args:
            assignment: The new assignment
        
        Returns:
            List of created notifications
        """
        notifications = []
        
        # Get all available responders in the assigned department
        from app.services.allocation import get_available_responders
        responders = get_available_responders(assignment.department_id)
        
        incident = assignment.incident
        
        for responder in responders:
            notification = self.notify_user(
                responder,
                NotificationType.NEW_ASSIGNMENT,
                f'New assignment: {incident.category.name} incident at {incident.location_text or "Unknown location"}',
                title='New Incident Assignment',
                priority=self._severity_to_priority(incident.severity),
                data={
                    'assignment_id': assignment.id,
                    'incident_id': incident.id,
                    'priority_rank': assignment.priority_rank
                },
                action_url=f'/responder/assignments/{assignment.id}',
                send_push=True
            )
            notifications.append(notification)
        
        return notifications
    
    def notify_status_change(
        self, 
        incident: IncidentReport, 
        old_status: str, 
        new_status: str
    ) -> List[Notification]:
        """
        Notify relevant parties about a status change.
        
        Args:
            incident: The incident
            old_status: Previous status
            new_status: New status
        
        Returns:
            List of created notifications
        """
        notifications = []
        
        # Notify the reporter (if not anonymous)
        if incident.user_id:
            reporter = User.query.get(incident.user_id)
            if reporter:
                notification = self.notify_user(
                    reporter,
                    NotificationType.INCIDENT_STATUS_CHANGED,
                    f'Your incident status updated: {old_status} → {new_status}',
                    data={'incident_id': incident.id, 'old_status': old_status, 'new_status': new_status},
                    action_url=f'/reports/{incident.id}'
                )
                notifications.append(notification)
        
        # If resolved, send confirmation
        if new_status == 'RESOLVED':
            if incident.user_id:
                reporter = User.query.get(incident.user_id)
                if reporter:
                    notification = self.notify_user(
                        reporter,
                        NotificationType.INCIDENT_RESOLVED,
                        'Your incident has been resolved. Thank you for reporting.',
                        priority=NotificationPriority.NORMAL,
                        data={'incident_id': incident.id},
                        action_url=f'/reports/{incident.id}',
                        send_email=True
                    )
                    notifications.append(notification)
        
        return notifications
    
    def notify_new_message(
        self, 
        incident: IncidentReport, 
        sender: User, 
        message_text: str
    ) -> List[Notification]:
        """
        Notify about a new message on an incident.
        
        Args:
            incident: The incident
            sender: Message sender
            message_text: The message content
        
        Returns:
            List of created notifications
        """
        notifications = []
        
        # Truncate message for notification
        preview = message_text[:100] + '...' if len(message_text) > 100 else message_text
        
        # If sender is responder/department, notify the reporter
        if sender.is_responder or sender.is_department or sender.is_staff:
            if incident.user_id and incident.user_id != sender.id:
                reporter = User.query.get(incident.user_id)
                if reporter:
                    notification = self.notify_user(
                        reporter,
                        NotificationType.NEW_MESSAGE,
                        f'New message on your incident: "{preview}"',
                        title='New Message',
                        data={'incident_id': incident.id, 'sender_id': sender.id},
                        action_url=f'/reports/{incident.id}',
                        send_push=True
                    )
                    notifications.append(notification)
        
        # If sender is reporter, notify assigned responders
        else:
            for assignment in incident.assignments.filter_by(status='ACCEPTED'):
                if assignment.responder_id and assignment.responder_id != sender.id:
                    responder = User.query.get(assignment.responder_id)
                    if responder:
                        notification = self.notify_user(
                            responder,
                            NotificationType.NEW_MESSAGE,
                            f'New message from reporter: "{preview}"',
                            title='New Message',
                            data={'incident_id': incident.id, 'assignment_id': assignment.id},
                            action_url=f'/responder/assignments/{assignment.id}',
                            send_push=True
                        )
                        notifications.append(notification)
        
        return notifications
    
    def broadcast_to_department(
        self, 
        department_id: int, 
        notification_type: str, 
        message: str,
        title: str = None,
        data: Dict[str, Any] = None
    ) -> List[Notification]:
        """
        Broadcast a notification to all users in a department.
        
        Args:
            department_id: Department ID
            notification_type: Type of notification
            message: Notification message
            title: Optional title
            data: Additional data
        
        Returns:
            List of created notifications
        """
        notifications = []
        
        users = User.query.filter(User.department_id == department_id).all()
        
        for user in users:
            notification = self.notify_user(
                user,
                notification_type,
                message,
                title=title,
                data=data
            )
            notifications.append(notification)
        
        return notifications
    
    def broadcast_safety_alert(
        self, 
        alert, 
        users: List[User] = None
    ) -> List[Notification]:
        """
        Broadcast a safety alert to users in the affected area.
        
        Args:
            alert: SafetyAlert object
            users: Optional list of users to notify (if None, finds users in area)
        
        Returns:
            List of created notifications
        """
        notifications = []
        
        if users is None:
            # For now, notify all users (in production, would filter by location)
            users = User.query.filter(User.is_staff == False).all()
        
        for user in users:
            notification = self.notify_user(
                user,
                NotificationType.SAFETY_ALERT,
                alert.message,
                title=alert.title,
                priority=self._alert_severity_to_priority(alert.severity),
                data={'alert_id': alert.id},
                send_push=True,
                send_sms=alert.severity == 'CRITICAL'
            )
            notifications.append(notification)
            alert.push_sent_count += 1
        
        db.session.commit()
        
        return notifications
    
    def mark_read(self, notification_id: int, user_id: int) -> bool:
        """
        Mark a notification as read.
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for verification)
        
        Returns:
            True if successful, False otherwise
        """
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user_id
        ).first()
        
        if notification:
            notification.mark_read()
            db.session.commit()
            return True
        
        return False
    
    def mark_all_read(self, user_id: int) -> int:
        """
        Mark all notifications as read for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Number of notifications marked as read
        """
        result = Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).update({
            'is_read': True,
            'read_at': datetime.utcnow()
        })
        
        db.session.commit()
        
        return result
    
    def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user."""
        return Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).count()
    
    def _get_default_title(self, notification_type: str) -> str:
        """Get default title for a notification type."""
        titles = {
            NotificationType.INCIDENT_CREATED: 'New Incident',
            NotificationType.INCIDENT_ASSIGNED: 'Incident Assigned',
            NotificationType.INCIDENT_STATUS_CHANGED: 'Status Update',
            NotificationType.INCIDENT_RESOLVED: 'Incident Resolved',
            NotificationType.NEW_ASSIGNMENT: 'New Assignment',
            NotificationType.ASSIGNMENT_UPDATED: 'Assignment Update',
            NotificationType.ASSIGNMENT_CANCELLED: 'Assignment Cancelled',
            NotificationType.NEW_MESSAGE: 'New Message',
            NotificationType.SAFETY_ALERT: 'Safety Alert',
            NotificationType.SYSTEM_ANNOUNCEMENT: 'Announcement',
            NotificationType.ESCALATION_TRIGGERED: 'Escalation Alert',
        }
        return titles.get(notification_type, 'Notification')
    
    def _severity_to_priority(self, severity: str) -> str:
        """Convert incident severity to notification priority."""
        mapping = {
            'CRITICAL': NotificationPriority.URGENT,
            'HIGH': NotificationPriority.HIGH,
            'MEDIUM': NotificationPriority.NORMAL,
            'LOW': NotificationPriority.LOW,
            'INFO': NotificationPriority.LOW,
        }
        return mapping.get(severity, NotificationPriority.NORMAL)
    
    def _alert_severity_to_priority(self, severity: str) -> str:
        """Convert alert severity to notification priority."""
        mapping = {
            'CRITICAL': NotificationPriority.URGENT,
            'WARNING': NotificationPriority.HIGH,
            'INFO': NotificationPriority.NORMAL,
        }
        return mapping.get(severity, NotificationPriority.NORMAL)
    
    def _send_websocket(self, user_id: int, notification: Notification):
        """Send notification via WebSocket."""
        if self.socketio:
            self.socketio.emit(
                'notification',
                {
                    'id': notification.id,
                    'type': notification.type,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'data': notification.data,
                    'action_url': notification.action_url,
                    'created_at': notification.created_at.isoformat()
                },
                room=f'user_{user_id}'
            )
    
    def _send_push_notification(self, user: User, notification: Notification):
        """Send push notification (placeholder for actual implementation)."""
        # In production, integrate with Firebase Cloud Messaging, OneSignal, etc.
        notification.mark_pushed()
        db.session.commit()
    
    def _send_email(self, user: User, notification: Notification):
        """Send email notification (placeholder for actual implementation)."""
        # In production, integrate with SendGrid, Mailgun, etc.
        notification.mark_emailed()
        db.session.commit()
    
    def _send_sms(self, user: User, notification: Notification):
        """Send SMS notification (placeholder for actual implementation)."""
        # In production, integrate with Twilio, Nexmo, etc.
        notification.mark_sms_sent()
        db.session.commit()

