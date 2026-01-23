"""
Message model for SafeAlert
"""
from datetime import datetime
from app.extensions import db


class IncidentMessage(db.Model):
    """Incident message model for admin-user communication"""
    __tablename__ = 'incident_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident_reports.id', ondelete='CASCADE'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        db.Index('idx_message_incident_created', 'incident_id', 'created_at'),
    )
    
    @property
    def sender_role(self):
        """Get sender role (admin or user)"""
        return 'admin' if self.sender.is_staff else 'user'
    
    def __repr__(self):
        return f'<IncidentMessage {self.id}>'


