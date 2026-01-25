"""
Escalation Service for SafeAlert

Handles automated escalation of incidents based on configurable rules.
"""
from datetime import datetime, timedelta
from typing import List, Optional

from app.extensions import db
from app.models import (
    IncidentReport,
    IncidentAssignment,
    AssignmentStatus,
    IncidentStatus,
    EscalationRule,
    EscalationLog,
    EscalationTrigger,
    EscalationAction,
    Department,
    User,
    StatusHistory,
)
from app.services.allocation import AllocationService, get_nearby_departments


class EscalationService:
    """
    Service for automated incident escalation.
    
    Monitors incidents for escalation triggers and executes configured actions.
    """
    
    def __init__(self):
        self.allocation_service = AllocationService()
    
    def check_all_escalations(self) -> List[EscalationLog]:
        """
        Check all active incidents for escalation triggers.
        This should be run periodically (e.g., every minute via cron/scheduler).
        
        Returns:
            List of EscalationLog entries created
        """
        logs = []
        
        # Check for NO_ACKNOWLEDGE triggers
        logs.extend(self._check_no_acknowledge())
        
        # Check for NO_ARRIVAL triggers
        logs.extend(self._check_no_arrival())
        
        # Check for SLA_BREACH triggers
        logs.extend(self._check_sla_breach())
        
        return logs
    
    def _check_no_acknowledge(self) -> List[EscalationLog]:
        """Check for assignments waiting too long for acknowledgment"""
        logs = []
        
        # Get active rules for this trigger type
        rules = EscalationRule.query.filter_by(
            trigger_type=EscalationTrigger.NO_ACKNOWLEDGE,
            is_active=True
        ).order_by(EscalationRule.priority).all()
        
        if not rules:
            return logs
        
        for rule in rules:
            threshold = datetime.utcnow() - timedelta(minutes=rule.trigger_threshold_minutes)
            
            # Find assignments in ASSIGNED status past threshold
            assignments = IncidentAssignment.query.filter(
                IncidentAssignment.status == AssignmentStatus.ASSIGNED,
                IncidentAssignment.assigned_at < threshold
            ).all()
            
            for assignment in assignments:
                incident = assignment.incident
                
                # Check if rule applies to this incident
                if not rule.matches_incident(incident):
                    continue
                
                # Check if already escalated for this trigger recently
                recent_escalation = EscalationLog.query.filter(
                    EscalationLog.incident_id == incident.id,
                    EscalationLog.assignment_id == assignment.id,
                    EscalationLog.trigger_type == EscalationTrigger.NO_ACKNOWLEDGE,
                    EscalationLog.triggered_at > threshold
                ).first()
                
                if recent_escalation:
                    continue
                
                # Execute escalation
                log = self._execute_escalation(rule, incident, assignment)
                if log:
                    logs.append(log)
        
        return logs
    
    def _check_no_arrival(self) -> List[EscalationLog]:
        """Check for responders who haven't arrived on scene"""
        logs = []
        
        rules = EscalationRule.query.filter_by(
            trigger_type=EscalationTrigger.NO_ARRIVAL,
            is_active=True
        ).order_by(EscalationRule.priority).all()
        
        if not rules:
            return logs
        
        for rule in rules:
            threshold = datetime.utcnow() - timedelta(minutes=rule.trigger_threshold_minutes)
            
            # Find assignments that are ACCEPTED or EN_ROUTE past threshold
            assignments = IncidentAssignment.query.filter(
                IncidentAssignment.status.in_([AssignmentStatus.ACCEPTED, AssignmentStatus.EN_ROUTE]),
                IncidentAssignment.acknowledged_at < threshold
            ).all()
            
            for assignment in assignments:
                incident = assignment.incident
                
                if not rule.matches_incident(incident):
                    continue
                
                recent_escalation = EscalationLog.query.filter(
                    EscalationLog.incident_id == incident.id,
                    EscalationLog.assignment_id == assignment.id,
                    EscalationLog.trigger_type == EscalationTrigger.NO_ARRIVAL,
                    EscalationLog.triggered_at > threshold
                ).first()
                
                if recent_escalation:
                    continue
                
                log = self._execute_escalation(rule, incident, assignment)
                if log:
                    logs.append(log)
        
        return logs
    
    def _check_sla_breach(self) -> List[EscalationLog]:
        """Check for SLA breaches on active incidents"""
        logs = []
        
        rules = EscalationRule.query.filter_by(
            trigger_type=EscalationTrigger.SLA_BREACH,
            is_active=True
        ).order_by(EscalationRule.priority).all()
        
        if not rules:
            return logs
        
        # Get active incidents
        active_incidents = IncidentReport.query.filter(
            IncidentReport.status.in_(IncidentStatus.ACTIVE_STATUSES)
        ).all()
        
        for incident in active_incidents:
            if not incident.is_sla_breached:
                continue
            
            for rule in rules:
                if not rule.matches_incident(incident):
                    continue
                
                # Check if already escalated
                recent_escalation = EscalationLog.query.filter(
                    EscalationLog.incident_id == incident.id,
                    EscalationLog.trigger_type == EscalationTrigger.SLA_BREACH,
                    EscalationLog.triggered_at > datetime.utcnow() - timedelta(minutes=rule.trigger_threshold_minutes)
                ).first()
                
                if recent_escalation:
                    continue
                
                log = self._execute_escalation(rule, incident)
                if log:
                    logs.append(log)
                    break  # Only one escalation per incident per check
        
        return logs
    
    def _execute_escalation(
        self, 
        rule: EscalationRule, 
        incident: IncidentReport,
        assignment: IncidentAssignment = None
    ) -> Optional[EscalationLog]:
        """
        Execute an escalation action based on the rule.
        
        Args:
            rule: The escalation rule to execute
            incident: The incident being escalated
            assignment: The assignment being escalated (if applicable)
        
        Returns:
            EscalationLog entry or None if failed
        """
        try:
            log = EscalationLog.create_from_rule(rule, incident, assignment)
            
            # Execute the action
            if rule.action_type == EscalationAction.ADD_DEPARTMENT:
                result = self._action_add_department(incident, rule.action_config)
                log.action_result = result
            
            elif rule.action_type == EscalationAction.REASSIGN:
                result = self._action_reassign(assignment, rule.action_config)
                log.action_result = result
            
            elif rule.action_type == EscalationAction.NOTIFY_SUPERVISOR:
                result = self._action_notify_supervisor(incident, assignment)
                log.action_result = result
            
            elif rule.action_type == EscalationAction.NOTIFY_DISPATCHER:
                result = self._action_notify_dispatcher(incident)
                log.action_result = result
            
            elif rule.action_type == EscalationAction.UPGRADE_SEVERITY:
                result = self._action_upgrade_severity(incident)
                log.action_result = result
            
            else:
                log.action_result = f"Unknown action type: {rule.action_type}"
                log.is_successful = False
            
            db.session.add(log)
            db.session.commit()
            
            return log
            
        except Exception as e:
            log = EscalationLog(
                incident_id=incident.id,
                assignment_id=assignment.id if assignment else None,
                rule_id=rule.id,
                trigger_type=rule.trigger_type,
                action_type=rule.action_type,
                is_successful=False,
                error_message=str(e)
            )
            db.session.add(log)
            db.session.commit()
            return log
    
    def _action_add_department(self, incident: IncidentReport, config: dict = None) -> str:
        """Add an additional department to the incident"""
        # Find nearest available department not already assigned
        current_dept_ids = [a.department_id for a in incident.assignments]
        
        nearby = get_nearby_departments(
            float(incident.latitude),
            float(incident.longitude),
            radius_km=config.get('radius_km', 50) if config else 50
        )
        
        for dept, distance in nearby:
            if dept.id not in current_dept_ids and dept.available_capacity > 0:
                new_assignment = self.allocation_service.add_department_to_incident(incident, dept.id)
                if new_assignment:
                    return f"Added department {dept.name} at {distance:.1f}km"
        
        return "No additional departments available"
    
    def _action_reassign(self, assignment: IncidentAssignment, config: dict = None) -> str:
        """Reassign to a different department"""
        if not assignment:
            return "No assignment to reassign"
        
        incident = assignment.incident
        current_dept_ids = [a.department_id for a in incident.assignments if a.status != AssignmentStatus.REASSIGNED]
        
        nearby = get_nearby_departments(
            float(incident.latitude),
            float(incident.longitude),
            radius_km=config.get('radius_km', 50) if config else 50
        )
        
        for dept, distance in nearby:
            if dept.id not in current_dept_ids and dept.available_capacity > 0:
                new_assignment = self.allocation_service.reassign_incident(
                    assignment, 
                    dept.id,
                    reason="Escalation: No acknowledgment received"
                )
                return f"Reassigned to {dept.name}"
        
        return "No alternative departments available for reassignment"
    
    def _action_notify_supervisor(self, incident: IncidentReport, assignment: IncidentAssignment = None) -> str:
        """Notify department supervisor"""
        from app.services.notification import NotificationService
        
        notification_service = NotificationService()
        
        if assignment and assignment.department:
            # Find supervisor (staff users in the department)
            supervisors = User.query.filter(
                User.department_id == assignment.department_id,
                User.is_staff == True
            ).all()
            
            for supervisor in supervisors:
                notification_service.notify_user(
                    supervisor,
                    'ESCALATION_TRIGGERED',
                    f'Incident #{incident.id} escalated - requires attention',
                    data={'incident_id': incident.id, 'assignment_id': assignment.id}
                )
            
            return f"Notified {len(supervisors)} supervisor(s)"
        
        return "No supervisors to notify"
    
    def _action_notify_dispatcher(self, incident: IncidentReport) -> str:
        """Notify all departments"""
        from app.services.notification import NotificationService
        
        notification_service = NotificationService()
        
        departments = User.query.filter(User.is_department == True).all()
        
        for department in departments:
            notification_service.notify_user(
                department,
                'ESCALATION_TRIGGERED',
                f'Incident #{incident.id} requires department attention',
                data={'incident_id': incident.id}
            )
        
        return f"Notified {len(departments)} department(s)"
    
    def _action_upgrade_severity(self, incident: IncidentReport) -> str:
        """Upgrade incident severity"""
        from app.models import IncidentSeverity
        
        severity_order = [IncidentSeverity.INFO, IncidentSeverity.LOW, IncidentSeverity.MEDIUM, IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]
        
        current_index = severity_order.index(incident.severity) if incident.severity in severity_order else 2
        
        if current_index < len(severity_order) - 1:
            old_severity = incident.severity
            incident.severity = severity_order[current_index + 1]
            
            history = StatusHistory(
                incident_id=incident.id,
                old_status=old_severity,
                new_status=incident.severity,
                notes='Severity upgraded due to escalation',
                source='ESCALATION'
            )
            db.session.add(history)
            
            return f"Severity upgraded from {old_severity} to {incident.severity}"
        
        return "Already at maximum severity"
    
    def manual_escalate(
        self, 
        incident: IncidentReport, 
        action_type: str, 
        triggered_by: User,
        reason: str = None
    ) -> EscalationLog:
        """
        Manually trigger an escalation.
        
        Args:
            incident: The incident to escalate
            action_type: The action to take
            triggered_by: The user triggering the escalation
            reason: Optional reason for escalation
        
        Returns:
            EscalationLog entry
        """
        log = EscalationLog.create_manual(incident, action_type, triggered_by, reason)
        
        try:
            if action_type == EscalationAction.ADD_DEPARTMENT:
                result = self._action_add_department(incident)
            elif action_type == EscalationAction.NOTIFY_DISPATCHER:
                result = self._action_notify_dispatcher(incident)
            elif action_type == EscalationAction.UPGRADE_SEVERITY:
                result = self._action_upgrade_severity(incident)
            else:
                result = f"Manual escalation: {action_type}"
            
            log.action_result = result
            log.is_successful = True
            
        except Exception as e:
            log.is_successful = False
            log.error_message = str(e)
        
        db.session.add(log)
        db.session.commit()
        
        return log

