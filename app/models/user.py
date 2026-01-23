"""
User model for SafeAlert
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    """User model with support for multiple roles"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(150), nullable=True, default='')
    last_name = db.Column(db.String(150), nullable=True, default='')
    phone_number = db.Column(db.String(20), nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    
    # Role flags (users can have multiple roles)
    is_staff = db.Column(db.Boolean, default=False, nullable=False)  # Admin
    is_dispatcher = db.Column(db.Boolean, default=False, nullable=False)  # Dispatcher
    is_responder = db.Column(db.Boolean, default=False, nullable=False)  # Field responder
    
    # Responder-specific fields
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True, index=True)
    badge_number = db.Column(db.String(50), nullable=True)
    specializations = db.Column(db.JSON, nullable=True)  # ["hazmat", "rescue", "ems"]
    is_on_duty = db.Column(db.Boolean, default=False, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    
    # Live location tracking (for responders)
    current_latitude = db.Column(db.Numeric(9, 6), nullable=True)
    current_longitude = db.Column(db.Numeric(9, 6), nullable=True)
    last_location_update = db.Column(db.DateTime, nullable=True)
    
    # Citizen-specific fields
    emergency_contacts = db.Column(db.JSON, nullable=True)  # [{"name": "...", "phone": "..."}]
    medical_info = db.Column(db.Text, nullable=True)  # Allergies, conditions (optional, encrypted)
    home_address = db.Column(db.String(255), nullable=True)
    home_latitude = db.Column(db.Numeric(9, 6), nullable=True)
    home_longitude = db.Column(db.Numeric(9, 6), nullable=True)
    
    # Notification preferences
    push_token = db.Column(db.String(255), nullable=True)  # For push notifications
    notification_preferences = db.Column(db.JSON, nullable=True)  # {"sms": true, "email": true, "push": true}
    
    # Timestamps
    date_joined = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    incidents = db.relationship('IncidentReport', backref='user', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='IncidentReport.user_id')
    sent_messages = db.relationship('IncidentMessage', backref='sender', lazy='dynamic', cascade='all, delete-orphan')
    status_changes = db.relationship('StatusHistory', backref='changed_by_user', lazy='dynamic', foreign_keys='StatusHistory.changed_by_id')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_user_role', 'is_staff', 'is_dispatcher', 'is_responder'),
        db.Index('idx_user_department', 'department_id'),
        db.Index('idx_user_on_duty', 'is_on_duty', 'is_available'),
    )
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def full_name(self):
        """Get user's full name"""
        parts = [self.first_name, self.last_name]
        return ' '.join(p for p in parts if p) or self.username
    
    @property
    def role_display(self):
        """Get display string for user's role(s)"""
        roles = []
        if self.is_staff:
            roles.append('Admin')
        if self.is_dispatcher:
            roles.append('Dispatcher')
        if self.is_responder:
            roles.append('Responder')
        if not roles:
            roles.append('Citizen')
        return ', '.join(roles)
    
    @property
    def is_field_ready(self):
        """Check if responder is ready to receive assignments"""
        return self.is_responder and self.is_on_duty and self.is_available
    
    def update_location(self, latitude, longitude):
        """Update responder's current location"""
        self.current_latitude = latitude
        self.current_longitude = longitude
        self.last_location_update = datetime.utcnow()
    
    def go_on_duty(self):
        """Set responder as on duty"""
        self.is_on_duty = True
        self.is_available = True
    
    def go_off_duty(self):
        """Set responder as off duty"""
        self.is_on_duty = False
        self.is_available = False
    
    def mark_busy(self):
        """Mark responder as busy (on assignment)"""
        self.is_available = False
    
    def mark_available(self):
        """Mark responder as available for new assignments"""
        if self.is_on_duty:
            self.is_available = True
