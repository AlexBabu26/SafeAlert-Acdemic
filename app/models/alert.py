"""
Safety Alert model for SafeAlert
"""
from datetime import datetime
from app.extensions import db


class AlertSeverity:
    """Alert severity levels"""
    INFO = 'INFO'           # Informational
    WARNING = 'WARNING'     # Warning
    CRITICAL = 'CRITICAL'   # Critical/Emergency
    
    CHOICES = [INFO, WARNING, CRITICAL]


class AlertType:
    """Alert type constants"""
    INCIDENT_AREA = 'INCIDENT_AREA'       # Alert about an incident in area
    WEATHER = 'WEATHER'                   # Weather warning
    EVACUATION = 'EVACUATION'             # Evacuation notice
    ROAD_CLOSURE = 'ROAD_CLOSURE'         # Road/area closure
    PUBLIC_SAFETY = 'PUBLIC_SAFETY'       # General public safety
    SYSTEM = 'SYSTEM'                     # System announcement
    
    CHOICES = [INCIDENT_AREA, WEATHER, EVACUATION, ROAD_CLOSURE, PUBLIC_SAFETY, SYSTEM]


class SafetyAlert(db.Model):
    """Public safety alert model for broadcasting warnings to citizens"""
    __tablename__ = 'safety_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Content
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    alert_type = db.Column(db.String(30), default='PUBLIC_SAFETY', nullable=False, index=True)
    severity = db.Column(db.String(20), default='INFO', nullable=False, index=True)
    
    # Instructions for public
    instructions = db.Column(db.Text, nullable=True)  # "Stay indoors", "Evacuate immediately"
    
    # Geographic targeting
    center_lat = db.Column(db.Numeric(9, 6), nullable=True)
    center_lng = db.Column(db.Numeric(9, 6), nullable=True)
    radius_km = db.Column(db.Float, nullable=True)  # Radius from center point
    
    # Alternative: polygon targeting
    coverage_polygon = db.Column(db.JSON, nullable=True)  # GeoJSON polygon
    
    # Citywide alert (no geo restriction)
    is_citywide = db.Column(db.Boolean, default=False, nullable=False)
    
    # Related incident (optional)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident_reports.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Timing
    active_from = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    active_until = db.Column(db.DateTime, nullable=True)  # Null = indefinite
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_expired = db.Column(db.Boolean, default=False, nullable=False)
    
    # Delivery stats
    push_sent_count = db.Column(db.Integer, default=0)
    sms_sent_count = db.Column(db.Integer, default=0)
    
    # Creator
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    incident = db.relationship('IncidentReport', backref=db.backref('alerts', lazy='dynamic'))
    created_by = db.relationship('User', backref='created_alerts')
    
    __table_args__ = (
        db.Index('idx_alert_active', 'is_active'),
        db.Index('idx_alert_severity', 'severity'),
        db.Index('idx_alert_location', 'center_lat', 'center_lng'),
        db.Index('idx_alert_timing', 'active_from', 'active_until'),
    )
    
    def __repr__(self):
        return f'<SafetyAlert {self.id} - {self.title}>'
    
    def deactivate(self):
        """Deactivate the alert"""
        self.is_active = False
    
    def expire(self):
        """Mark alert as expired"""
        self.is_expired = True
        self.is_active = False
    
    def extend(self, until):
        """Extend alert active period"""
        self.active_until = until
        self.is_expired = False
        self.is_active = True
    
    @property
    def is_currently_active(self):
        """Check if alert is currently active based on time window"""
        now = datetime.utcnow()
        
        if not self.is_active:
            return False
        
        if self.active_from and now < self.active_from:
            return False
        
        if self.active_until and now > self.active_until:
            return False
        
        return True
    
    def is_in_range(self, latitude, longitude):
        """Check if a location is within the alert's coverage area"""
        if self.is_citywide:
            return True
        
        if self.center_lat is None or self.center_lng is None:
            return True  # No geo restriction
        
        if self.radius_km is None:
            return True
        
        # Calculate distance (simplified, using Haversine would be more accurate)
        from app.utils.geo import calculate_distance
        distance = calculate_distance(
            float(self.center_lat), float(self.center_lng),
            float(latitude), float(longitude)
        )
        
        return distance <= self.radius_km
    
    @classmethod
    def create_for_incident(cls, incident, title, message, radius_km=5.0, created_by=None):
        """Create an alert related to an incident"""
        return cls(
            title=title,
            message=message,
            alert_type=AlertType.INCIDENT_AREA,
            severity=AlertSeverity.WARNING if incident.severity in ['CRITICAL', 'HIGH'] else AlertSeverity.INFO,
            center_lat=incident.latitude,
            center_lng=incident.longitude,
            radius_km=radius_km,
            incident_id=incident.id,
            created_by_id=created_by.id if created_by else None
        )
    
    @classmethod
    def create_evacuation_alert(cls, title, message, center_lat, center_lng, radius_km, created_by=None):
        """Create an evacuation alert"""
        return cls(
            title=title,
            message=message,
            alert_type=AlertType.EVACUATION,
            severity=AlertSeverity.CRITICAL,
            instructions='Please evacuate the area immediately and follow official guidance.',
            center_lat=center_lat,
            center_lng=center_lng,
            radius_km=radius_km,
            created_by_id=created_by.id if created_by else None
        )

