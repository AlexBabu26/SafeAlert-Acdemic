"""
Department and Resource models for SafeAlert
"""
from datetime import datetime
from app.extensions import db


class DepartmentType:
    """Department type constants"""
    FIRE = 'FIRE'
    POLICE = 'POLICE'
    MEDICAL = 'MEDICAL'
    RESCUE = 'RESCUE'
    HAZMAT = 'HAZMAT'
    TRAFFIC = 'TRAFFIC'
    
    CHOICES = [FIRE, POLICE, MEDICAL, RESCUE, HAZMAT, TRAFFIC]


class ResourceType:
    """Resource type constants"""
    VEHICLE = 'VEHICLE'
    EQUIPMENT = 'EQUIPMENT'
    PERSONNEL = 'PERSONNEL'
    
    CHOICES = [VEHICLE, EQUIPMENT, PERSONNEL]


class ResourceStatus:
    """Resource status constants"""
    AVAILABLE = 'AVAILABLE'
    DEPLOYED = 'DEPLOYED'
    MAINTENANCE = 'MAINTENANCE'
    OUT_OF_SERVICE = 'OUT_OF_SERVICE'
    
    CHOICES = [AVAILABLE, DEPLOYED, MAINTENANCE, OUT_OF_SERVICE]


class Department(db.Model):
    """Department model for emergency service units"""
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)  # e.g., "Station 5 - Downtown Fire"
    code = db.Column(db.String(20), unique=True, nullable=False)  # e.g., "FD-05"
    
    # Classification
    type = db.Column(db.String(30), nullable=False, index=True)  # FIRE, POLICE, MEDICAL, etc.
    description = db.Column(db.Text, nullable=True, default='')
    
    # Hierarchy (optional parent department)
    parent_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # Location & coverage
    headquarters_lat = db.Column(db.Numeric(9, 6), nullable=False)
    headquarters_lng = db.Column(db.Numeric(9, 6), nullable=False)
    address = db.Column(db.String(255), nullable=True, default='')
    coverage_radius_km = db.Column(db.Float, default=15.0)
    coverage_polygon = db.Column(db.JSON, nullable=True)  # GeoJSON for complex coverage areas
    
    # Capacity
    max_concurrent_incidents = db.Column(db.Integer, default=5)
    current_active_incidents = db.Column(db.Integer, default=0)
    
    # Contact
    dispatch_phone = db.Column(db.String(20), nullable=True)
    dispatch_email = db.Column(db.String(100), nullable=True)
    
    # Operating hours
    operating_hours = db.Column(db.JSON, nullable=True)  # {"mon": "08:00-18:00", ...}
    is_24_7 = db.Column(db.Boolean, default=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    responders = db.relationship('User', backref='department', lazy='dynamic', foreign_keys='User.department_id')
    resources = db.relationship('Resource', backref='department', lazy='dynamic', cascade='all, delete-orphan')
    assignments = db.relationship('IncidentAssignment', backref='department', lazy='dynamic')
    child_departments = db.relationship('Department', backref=db.backref('parent_department', remote_side=[id]), lazy='dynamic')
    
    __table_args__ = (
        db.Index('idx_department_type', 'type'),
        db.Index('idx_department_active', 'is_active'),
        db.Index('idx_department_location', 'headquarters_lat', 'headquarters_lng'),
    )
    
    def __repr__(self):
        return f'<Department {self.code} - {self.name}>'
    
    @property
    def available_capacity(self):
        """Calculate remaining capacity for new incidents"""
        return max(0, self.max_concurrent_incidents - self.current_active_incidents)
    
    @property
    def utilization_rate(self):
        """Calculate current utilization percentage"""
        if self.max_concurrent_incidents == 0:
            return 100.0
        return (self.current_active_incidents / self.max_concurrent_incidents) * 100
    
    def increment_active_incidents(self):
        """Increment active incident count"""
        self.current_active_incidents = min(
            self.current_active_incidents + 1,
            self.max_concurrent_incidents
        )
    
    def decrement_active_incidents(self):
        """Decrement active incident count"""
        self.current_active_incidents = max(0, self.current_active_incidents - 1)


class Resource(db.Model):
    """Resource model for tracking vehicles, equipment, and personnel"""
    __tablename__ = 'resources'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Identification
    type = db.Column(db.String(30), nullable=False)  # VEHICLE, EQUIPMENT, PERSONNEL
    name = db.Column(db.String(100), nullable=False)  # "Engine 5", "Ambulance A3"
    identifier = db.Column(db.String(50), nullable=True)  # License plate, serial number, badge
    description = db.Column(db.Text, nullable=True, default='')
    
    # Status
    status = db.Column(db.String(20), default='AVAILABLE', nullable=False, index=True)
    current_incident_id = db.Column(db.Integer, db.ForeignKey('incident_reports.id', ondelete='SET NULL'), nullable=True)
    
    # For mobile resources with GPS
    current_lat = db.Column(db.Numeric(9, 6), nullable=True)
    current_lng = db.Column(db.Numeric(9, 6), nullable=True)
    last_location_update = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    capacity = db.Column(db.Integer, nullable=True)  # e.g., seats in vehicle
    specifications = db.Column(db.JSON, nullable=True)  # Additional specs
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        db.Index('idx_resource_status', 'status'),
        db.Index('idx_resource_type', 'type'),
    )
    
    def __repr__(self):
        return f'<Resource {self.name} ({self.type})>'
    
    def mark_deployed(self, incident_id):
        """Mark resource as deployed to an incident"""
        self.status = ResourceStatus.DEPLOYED
        self.current_incident_id = incident_id
    
    def mark_available(self):
        """Mark resource as available"""
        self.status = ResourceStatus.AVAILABLE
        self.current_incident_id = None

