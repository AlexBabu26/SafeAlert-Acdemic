"""
Incident Assignment model for SafeAlert
"""
from datetime import datetime
from app.extensions import db


class AssignmentStatus:
    """Assignment status constants"""
    ASSIGNED = 'ASSIGNED'       # Newly assigned, awaiting acknowledgment
    ACCEPTED = 'ACCEPTED'       # Responder accepted the assignment
    EN_ROUTE = 'EN_ROUTE'       # Responder is traveling to incident
    ON_SCENE = 'ON_SCENE'       # Responder arrived at incident
    COMPLETED = 'COMPLETED'     # Assignment completed
    DECLINED = 'DECLINED'       # Responder declined the assignment
    REASSIGNED = 'REASSIGNED'   # Reassigned to another department
    CANCELLED = 'CANCELLED'     # Assignment cancelled
    
    CHOICES = [ASSIGNED, ACCEPTED, EN_ROUTE, ON_SCENE, COMPLETED, DECLINED, REASSIGNED, CANCELLED]
    
    # Statuses that count as "active"
    ACTIVE_STATUSES = [ASSIGNED, ACCEPTED, EN_ROUTE, ON_SCENE]


class IncidentAssignment(db.Model):
    """Tracks assignment of incidents to departments and responders"""
    __tablename__ = 'incident_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident_reports.id', ondelete='CASCADE'), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Optional: specific responder assigned (can be null if department-level assignment)
    responder_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Allocation metrics (calculated at assignment time)
    priority_rank = db.Column(db.Integer, nullable=False, default=1)  # 1 = highest priority (closest)
    distance_km = db.Column(db.Float, nullable=True)
    allocation_score = db.Column(db.Float, nullable=True)  # Multi-factor score (0-100)
    score_breakdown = db.Column(db.JSON, nullable=True)  # {"distance": 85, "workload": 70, ...}
    
    # Status tracking
    status = db.Column(db.String(20), default='ASSIGNED', nullable=False, index=True)
    
    # Timestamps for SLA tracking
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)  # When responder accepted
    en_route_at = db.Column(db.DateTime, nullable=True)      # When responder started traveling
    arrived_at = db.Column(db.DateTime, nullable=True)       # When responder reached scene
    completed_at = db.Column(db.DateTime, nullable=True)     # When assignment was completed
    
    # Response metrics (calculated)
    acknowledgment_time_seconds = db.Column(db.Integer, nullable=True)  # Time to accept
    travel_time_seconds = db.Column(db.Integer, nullable=True)          # Time from en_route to arrival
    total_response_time_seconds = db.Column(db.Integer, nullable=True)  # Total time from assigned to arrived
    
    # Notes and communication
    notes = db.Column(db.Text, nullable=True, default='')
    decline_reason = db.Column(db.String(255), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    incident = db.relationship('IncidentReport', backref=db.backref('assignments', lazy='dynamic', cascade='all, delete-orphan'))
    responder = db.relationship('User', backref=db.backref('assignments', lazy='dynamic'), foreign_keys=[responder_id])
    
    __table_args__ = (
        db.Index('idx_assignment_incident_dept', 'incident_id', 'department_id'),
        db.Index('idx_assignment_status', 'status'),
        db.Index('idx_assignment_assigned_at', 'assigned_at'),
        db.UniqueConstraint('incident_id', 'department_id', name='uq_incident_department'),
    )
    
    def __repr__(self):
        return f'<IncidentAssignment {self.id} - Incident {self.incident_id} to Dept {self.department_id}>'
    
    def accept(self, responder_id=None):
        """Mark assignment as accepted"""
        self.status = AssignmentStatus.ACCEPTED
        self.acknowledged_at = datetime.utcnow()
        if responder_id:
            self.responder_id = responder_id
        
        # Calculate acknowledgment time
        if self.assigned_at:
            delta = self.acknowledged_at - self.assigned_at
            self.acknowledgment_time_seconds = int(delta.total_seconds())
    
    def mark_en_route(self):
        """Mark responder as en route to incident"""
        self.status = AssignmentStatus.EN_ROUTE
        self.en_route_at = datetime.utcnow()
    
    def mark_arrived(self):
        """Mark responder as arrived at scene"""
        self.status = AssignmentStatus.ON_SCENE
        self.arrived_at = datetime.utcnow()
        
        # Calculate travel time
        if self.en_route_at:
            delta = self.arrived_at - self.en_route_at
            self.travel_time_seconds = int(delta.total_seconds())
        
        # Calculate total response time
        if self.assigned_at:
            delta = self.arrived_at - self.assigned_at
            self.total_response_time_seconds = int(delta.total_seconds())
    
    def complete(self, notes=None):
        """Mark assignment as completed"""
        self.status = AssignmentStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if notes:
            self.notes = notes
    
    def decline(self, reason=None):
        """Decline the assignment"""
        self.status = AssignmentStatus.DECLINED
        self.decline_reason = reason
    
    def reassign(self):
        """Mark as reassigned (before creating new assignment)"""
        self.status = AssignmentStatus.REASSIGNED
    
    @property
    def is_active(self):
        """Check if assignment is currently active"""
        return self.status in AssignmentStatus.ACTIVE_STATUSES
    
    @property
    def response_time_minutes(self):
        """Get total response time in minutes"""
        if self.total_response_time_seconds:
            return self.total_response_time_seconds / 60
        return None

