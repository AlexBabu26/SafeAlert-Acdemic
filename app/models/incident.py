"""
Incident-related models for SafeAlert
"""
from datetime import datetime
from sqlalchemy import Enum, Index
import enum
import secrets
import string
from app.extensions import db


class IncidentStatus:
    """Incident status choices - expanded for full workflow"""
    REPORTED = 'REPORTED'         # Initial submission
    VERIFIED = 'VERIFIED'         # Admin verified as legitimate
    DISPATCHED = 'DISPATCHED'     # Assigned to department(s)
    ACKNOWLEDGED = 'ACKNOWLEDGED' # Responder accepted
    EN_ROUTE = 'EN_ROUTE'         # Responder traveling
    ON_SCENE = 'ON_SCENE'         # Responder arrived
    RESOLVED = 'RESOLVED'         # Issue addressed
    CLOSED = 'CLOSED'             # Fully closed
    CANCELLED = 'CANCELLED'       # Report cancelled
    
    CHOICES = [REPORTED, VERIFIED, DISPATCHED, ACKNOWLEDGED, EN_ROUTE, ON_SCENE, RESOLVED, CLOSED, CANCELLED]
    
    # Statuses that count as "active" (not yet resolved)
    ACTIVE_STATUSES = [REPORTED, VERIFIED, DISPATCHED, ACKNOWLEDGED, EN_ROUTE, ON_SCENE]
    
    # Legacy mapping for backward compatibility
    LEGACY_MAP = {
        'PENDING': REPORTED,
    }


class IncidentSeverity:
    """Incident severity levels"""
    CRITICAL = 'CRITICAL'   # Life-threatening, immediate response
    HIGH = 'HIGH'           # Serious, rapid response needed
    MEDIUM = 'MEDIUM'       # Important but not life-threatening
    LOW = 'LOW'             # Minor, can be scheduled
    INFO = 'INFO'           # Informational only, no response needed
    
    CHOICES = [CRITICAL, HIGH, MEDIUM, LOW, INFO]
    
    # SLA targets in minutes by severity
    SLA_TARGETS = {
        CRITICAL: 5,
        HIGH: 15,
        MEDIUM: 30,
        LOW: 60,
        INFO: None,  # No SLA
    }


class Category(db.Model):
    """Category model for incident types"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True, default='')
    icon = db.Column(db.String(50), nullable=True, default='')  # Icon name or emoji
    color = db.Column(db.String(20), nullable=True, default='')  # Color code for UI
    default_severity = db.Column(db.String(20), default='MEDIUM', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    priority_order = db.Column(db.Integer, default=0)  # For sorting
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    incidents = db.relationship('IncidentReport', backref='category', lazy='dynamic')
    department_mappings = db.relationship('CategoryDepartmentMapping', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_category_name', 'name'),
        db.Index('idx_category_active', 'is_active'),
    )
    
    def __repr__(self):
        return f'<Category {self.name}>'


class CategoryDepartmentMapping(db.Model):
    """Maps incident categories to department types with priority"""
    __tablename__ = 'category_department_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False, index=True)
    department_type = db.Column(db.String(30), nullable=False)  # FIRE, POLICE, MEDICAL, etc.
    priority = db.Column(db.Integer, default=1, nullable=False)  # 1 = primary, 2 = secondary, etc.
    is_required = db.Column(db.Boolean, default=True)  # Must be assigned or optional
    
    __table_args__ = (
        db.Index('idx_mapping_category_priority', 'category_id', 'priority'),
        db.UniqueConstraint('category_id', 'department_type', name='uq_category_dept_type'),
    )
    
    def __repr__(self):
        return f'<CategoryDepartmentMapping {self.category_id} -> {self.department_type}>'


def generate_tracking_code():
    """Generate a unique tracking code for anonymous reports"""
    prefix = 'SA'
    year = datetime.utcnow().year
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f'{prefix}-{year}-{random_part}'


class IncidentReport(db.Model):
    """Incident report model with enhanced tracking"""
    __tablename__ = 'incident_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Reporter info (nullable for anonymous reports)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    anonymous_tracking_code = db.Column(db.String(20), unique=True, nullable=True, index=True)
    
    # Classification
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    severity = db.Column(db.String(20), default='MEDIUM', nullable=False, index=True)
    
    # Content
    title = db.Column(db.String(200), nullable=True, default='')
    description = db.Column(db.Text, nullable=False)
    
    # Location
    location_text = db.Column(db.String(500), nullable=True, default='')
    address_formatted = db.Column(db.String(255), nullable=True)  # Reverse geocoded
    landmark_description = db.Column(db.String(255), nullable=True)  # "Near the red building"
    latitude = db.Column(db.Numeric(9, 6), nullable=True)
    longitude = db.Column(db.Numeric(9, 6), nullable=True)
    
    # Status
    status = db.Column(db.String(20), default='REPORTED', nullable=False, index=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)  # Confirmed by responder on scene
    
    # SLA timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    dispatch_time = db.Column(db.DateTime, nullable=True)      # When assigned to department
    acknowledge_time = db.Column(db.DateTime, nullable=True)   # When responder accepted
    arrival_time = db.Column(db.DateTime, nullable=True)       # When responder on scene
    resolution_time = db.Column(db.DateTime, nullable=True)    # When marked resolved
    closed_time = db.Column(db.DateTime, nullable=True)        # When fully closed
    
    # Response metrics (calculated)
    dispatch_response_seconds = db.Column(db.Integer, nullable=True)   # Created -> Dispatched
    total_response_seconds = db.Column(db.Integer, nullable=True)      # Created -> Arrival
    resolution_seconds = db.Column(db.Integer, nullable=True)          # Created -> Resolved
    
    # Impact assessment
    estimated_affected_people = db.Column(db.Integer, nullable=True)
    requires_evacuation = db.Column(db.Boolean, default=False)
    
    # Follow-up
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_notes = db.Column(db.Text, nullable=True)
    follow_up_date = db.Column(db.DateTime, nullable=True)
    
    # Additional metadata
    source = db.Column(db.String(30), default='WEB', nullable=False)  # WEB, MOBILE, QUICK, API
    ip_address = db.Column(db.String(45), nullable=True)  # For abuse prevention
    user_agent = db.Column(db.String(255), nullable=True)
    
    # Timestamps
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    attachments = db.relationship('IncidentAttachment', backref='incident', lazy='dynamic', cascade='all, delete-orphan')
    status_history = db.relationship('StatusHistory', backref='incident', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('IncidentMessage', backref='incident', lazy='dynamic', cascade='all, delete-orphan')
    media = db.relationship('IncidentMedia', backref='incident', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_incident_created_at', 'created_at'),
        Index('idx_incident_status', 'status'),
        Index('idx_incident_severity', 'severity'),
        Index('idx_incident_user_created', 'user_id', 'created_at'),
        Index('idx_incident_location', 'latitude', 'longitude'),
        Index('idx_incident_tracking', 'anonymous_tracking_code'),
    )
    
    def __repr__(self):
        return f'<IncidentReport {self.id} - {self.status}>'
    
    @staticmethod
    def create_anonymous(category_id, description, **kwargs):
        """Create an anonymous incident report"""
        return IncidentReport(
            user_id=None,
            is_anonymous=True,
            anonymous_tracking_code=generate_tracking_code(),
            category_id=category_id,
            description=description,
            **kwargs
        )
    
    def dispatch(self):
        """Mark incident as dispatched"""
        self.status = IncidentStatus.DISPATCHED
        self.dispatch_time = datetime.utcnow()
        if self.created_at:
            delta = self.dispatch_time - self.created_at
            self.dispatch_response_seconds = int(delta.total_seconds())
    
    def acknowledge(self):
        """Mark incident as acknowledged by responder"""
        self.status = IncidentStatus.ACKNOWLEDGED
        self.acknowledge_time = datetime.utcnow()
    
    def mark_en_route(self):
        """Mark responder as en route"""
        self.status = IncidentStatus.EN_ROUTE
    
    def mark_on_scene(self):
        """Mark responder as arrived on scene"""
        self.status = IncidentStatus.ON_SCENE
        self.arrival_time = datetime.utcnow()
        if self.created_at:
            delta = self.arrival_time - self.created_at
            self.total_response_seconds = int(delta.total_seconds())
    
    def resolve(self):
        """Mark incident as resolved"""
        self.status = IncidentStatus.RESOLVED
        self.resolution_time = datetime.utcnow()
        if self.created_at:
            delta = self.resolution_time - self.created_at
            self.resolution_seconds = int(delta.total_seconds())
    
    def close(self):
        """Mark incident as closed"""
        self.status = IncidentStatus.CLOSED
        self.closed_time = datetime.utcnow()
    
    @property
    def is_active(self):
        """Check if incident is still active"""
        return self.status in IncidentStatus.ACTIVE_STATUSES
    
    @property
    def sla_target_minutes(self):
        """Get SLA target for this incident's severity"""
        return IncidentSeverity.SLA_TARGETS.get(self.severity)
    
    @property
    def is_sla_breached(self):
        """Check if SLA has been breached"""
        target = self.sla_target_minutes
        if target is None:
            return False
        
        if self.arrival_time:
            # Already responded, check actual response time
            if self.total_response_seconds:
                return (self.total_response_seconds / 60) > target
        else:
            # Still waiting, check elapsed time
            elapsed = datetime.utcnow() - self.created_at
            return (elapsed.total_seconds() / 60) > target
        
        return False


class IncidentAttachment(db.Model):
    """Incident attachment model (legacy, kept for backward compatibility)"""
    __tablename__ = 'incident_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident_reports.id', ondelete='CASCADE'), nullable=False, index=True)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        db.Index('idx_attachment_uploaded_at', 'uploaded_at'),
    )
    
    def __repr__(self):
        return f'<IncidentAttachment {self.id}>'


class IncidentMedia(db.Model):
    """Enhanced media attachment model with metadata"""
    __tablename__ = 'incident_media'
    
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident_reports.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # File info
    file_path = db.Column(db.String(500), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)  # IMAGE, VIDEO, AUDIO, DOCUMENT
    mime_type = db.Column(db.String(100), nullable=True)
    file_size_bytes = db.Column(db.Integer, nullable=True)
    
    # For audio/video
    duration_seconds = db.Column(db.Integer, nullable=True)
    
    # Thumbnail for images/videos
    thumbnail_path = db.Column(db.String(500), nullable=True)
    
    # Capture metadata
    captured_at = db.Column(db.DateTime, nullable=True)
    captured_latitude = db.Column(db.Numeric(9, 6), nullable=True)
    captured_longitude = db.Column(db.Numeric(9, 6), nullable=True)
    
    # Processing status
    is_processed = db.Column(db.Boolean, default=False)
    processing_notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        db.Index('idx_media_type', 'media_type'),
        db.Index('idx_media_uploaded_at', 'uploaded_at'),
    )
    
    def __repr__(self):
        return f'<IncidentMedia {self.id} ({self.media_type})>'


class StatusHistory(db.Model):
    """Status history model for tracking incident status changes"""
    __tablename__ = 'status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident_reports.id', ondelete='CASCADE'), nullable=False, index=True)
    old_status = db.Column(db.String(20), nullable=True, default='')
    new_status = db.Column(db.String(20), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True, default='')
    
    # Additional context
    source = db.Column(db.String(30), nullable=True)  # API, SYSTEM, ESCALATION
    assignment_id = db.Column(db.Integer, db.ForeignKey('incident_assignments.id', ondelete='SET NULL'), nullable=True)
    
    __table_args__ = (
        db.Index('idx_status_history_changed_at', 'changed_at'),
        db.Index('idx_status_history_incident_changed', 'incident_id', 'changed_at'),
    )
    
    def __repr__(self):
        return f'<StatusHistory {self.old_status} -> {self.new_status}>'
