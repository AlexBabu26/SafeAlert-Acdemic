"""
Escalation models for SafeAlert
"""
from datetime import datetime
from app.extensions import db


class EscalationTrigger:
    """Escalation trigger type constants"""
    NO_ACKNOWLEDGE = 'NO_ACKNOWLEDGE'       # Responder didn't acknowledge in time
    NO_ARRIVAL = 'NO_ARRIVAL'               # Responder didn't arrive in time
    NO_RESOLUTION = 'NO_RESOLUTION'         # Incident not resolved in time
    SEVERITY_UPGRADE = 'SEVERITY_UPGRADE'   # Severity was upgraded
    MANUAL = 'MANUAL'                       # Manually triggered by dispatcher
    SLA_BREACH = 'SLA_BREACH'               # SLA target exceeded
    
    CHOICES = [NO_ACKNOWLEDGE, NO_ARRIVAL, NO_RESOLUTION, SEVERITY_UPGRADE, MANUAL, SLA_BREACH]


class EscalationAction:
    """Escalation action type constants"""
    REASSIGN = 'REASSIGN'                   # Reassign to another department
    ADD_DEPARTMENT = 'ADD_DEPARTMENT'       # Add additional department
    NOTIFY_SUPERVISOR = 'NOTIFY_SUPERVISOR' # Notify supervisor/manager
    NOTIFY_DISPATCHER = 'NOTIFY_DISPATCHER' # Notify dispatcher
    BROADCAST_ALERT = 'BROADCAST_ALERT'     # Broadcast safety alert
    UPGRADE_SEVERITY = 'UPGRADE_SEVERITY'   # Increase severity level
    
    CHOICES = [REASSIGN, ADD_DEPARTMENT, NOTIFY_SUPERVISOR, NOTIFY_DISPATCHER, BROADCAST_ALERT, UPGRADE_SEVERITY]


class EscalationRule(db.Model):
    """Rules for automated escalation"""
    __tablename__ = 'escalation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Trigger conditions
    trigger_type = db.Column(db.String(30), nullable=False, index=True)
    trigger_threshold_minutes = db.Column(db.Integer, nullable=False)  # Time before trigger
    
    # Filters (when to apply this rule)
    severity_filter = db.Column(db.JSON, nullable=True)  # ["CRITICAL", "HIGH"] or null for all
    category_filter = db.Column(db.JSON, nullable=True)  # [1, 2, 3] category IDs or null for all
    department_type_filter = db.Column(db.JSON, nullable=True)  # ["FIRE", "POLICE"] or null for all
    
    # Action to take
    action_type = db.Column(db.String(30), nullable=False)
    action_config = db.Column(db.JSON, nullable=True)  # Additional action parameters
    
    # Priority for rule ordering
    priority = db.Column(db.Integer, default=0)  # Lower = higher priority
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    logs = db.relationship('EscalationLog', backref='rule', lazy='dynamic')
    
    __table_args__ = (
        db.Index('idx_escalation_rule_trigger', 'trigger_type'),
        db.Index('idx_escalation_rule_active', 'is_active'),
    )
    
    def __repr__(self):
        return f'<EscalationRule {self.name}>'
    
    def matches_incident(self, incident):
        """Check if rule applies to a given incident"""
        # Check severity filter
        if self.severity_filter:
            if incident.severity not in self.severity_filter:
                return False
        
        # Check category filter
        if self.category_filter:
            if incident.category_id not in self.category_filter:
                return False
        
        return True
    
    def matches_assignment(self, assignment):
        """Check if rule applies to a given assignment"""
        # Check department type filter
        if self.department_type_filter:
            if assignment.department.type not in self.department_type_filter:
                return False
        
        return True


class EscalationLog(db.Model):
    """Log of escalation events"""
    __tablename__ = 'escalation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Related entities
    incident_id = db.Column(db.Integer, db.ForeignKey('incident_reports.id', ondelete='CASCADE'), nullable=False, index=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('incident_assignments.id', ondelete='SET NULL'), nullable=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('escalation_rules.id', ondelete='SET NULL'), nullable=True)
    
    # Trigger details
    trigger_type = db.Column(db.String(30), nullable=False)
    trigger_reason = db.Column(db.Text, nullable=True)  # Human-readable explanation
    
    # Action taken
    action_type = db.Column(db.String(30), nullable=False)
    action_result = db.Column(db.Text, nullable=True)  # Result/outcome description
    action_data = db.Column(db.JSON, nullable=True)  # Additional data about action
    
    # Status
    is_successful = db.Column(db.Boolean, default=True, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    
    # Who triggered (null for automated)
    triggered_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Timestamps
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    incident = db.relationship('IncidentReport', backref=db.backref('escalation_logs', lazy='dynamic'))
    triggered_by = db.relationship('User', backref='triggered_escalations')
    
    __table_args__ = (
        db.Index('idx_escalation_log_incident', 'incident_id'),
        db.Index('idx_escalation_log_triggered_at', 'triggered_at'),
    )
    
    def __repr__(self):
        return f'<EscalationLog {self.id} - {self.trigger_type}>'
    
    @classmethod
    def create_from_rule(cls, rule, incident, assignment=None, triggered_by=None):
        """Create an escalation log entry from a rule execution"""
        return cls(
            incident_id=incident.id,
            assignment_id=assignment.id if assignment else None,
            rule_id=rule.id,
            trigger_type=rule.trigger_type,
            trigger_reason=f'Rule "{rule.name}" triggered after {rule.trigger_threshold_minutes} minutes',
            action_type=rule.action_type,
            triggered_by_id=triggered_by.id if triggered_by else None
        )
    
    @classmethod
    def create_manual(cls, incident, action_type, triggered_by, reason=None):
        """Create a manual escalation log entry"""
        return cls(
            incident_id=incident.id,
            trigger_type=EscalationTrigger.MANUAL,
            trigger_reason=reason or 'Manual escalation by dispatcher',
            action_type=action_type,
            triggered_by_id=triggered_by.id
        )

