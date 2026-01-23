"""
Assignment-related schemas for SafeAlert
"""
from marshmallow import Schema, fields, validate


class IncidentAssignmentSchema(Schema):
    """Schema for IncidentAssignment serialization"""
    id = fields.Int(dump_only=True)
    incident_id = fields.Int()
    department_id = fields.Int()
    responder_id = fields.Int(allow_none=True)
    
    # Department info
    department_name = fields.Str(attribute='department.name', dump_only=True)
    department_code = fields.Str(attribute='department.code', dump_only=True)
    department_type = fields.Str(attribute='department.type', dump_only=True)
    
    # Responder info
    responder_name = fields.Method('get_responder_name', dump_only=True)
    
    # Metrics
    priority_rank = fields.Int()
    distance_km = fields.Float(allow_none=True)
    allocation_score = fields.Float(allow_none=True)
    score_breakdown = fields.Dict(allow_none=True)
    
    # Status
    status = fields.Str()
    
    # Timestamps
    assigned_at = fields.DateTime()
    acknowledged_at = fields.DateTime(allow_none=True)
    en_route_at = fields.DateTime(allow_none=True)
    arrived_at = fields.DateTime(allow_none=True)
    completed_at = fields.DateTime(allow_none=True)
    
    # Calculated metrics
    acknowledgment_time_seconds = fields.Int(allow_none=True)
    travel_time_seconds = fields.Int(allow_none=True)
    total_response_time_seconds = fields.Int(allow_none=True)
    response_time_minutes = fields.Float(allow_none=True, dump_only=True)
    
    # Notes
    notes = fields.Str(allow_none=True)
    decline_reason = fields.Str(allow_none=True)
    
    # Status flags
    is_active = fields.Bool(dump_only=True)
    
    def get_responder_name(self, obj):
        if obj.responder:
            return obj.responder.full_name
        return None


class AssignmentStatusUpdateSchema(Schema):
    """Schema for updating assignment status"""
    status = fields.Str(required=True, validate=validate.OneOf([
        'ACCEPTED', 'EN_ROUTE', 'ON_SCENE', 'COMPLETED', 'DECLINED'
    ]))
    notes = fields.Str(allow_none=True)
    decline_reason = fields.Str(allow_none=True)


class AssignmentListSchema(Schema):
    """Schema for assignment list (minimal fields for dashboard)"""
    id = fields.Int(dump_only=True)
    incident_id = fields.Int()
    department_id = fields.Int()
    department_name = fields.Str(attribute='department.name', dump_only=True)
    
    # Incident summary
    incident_title = fields.Str(attribute='incident.title', dump_only=True)
    incident_severity = fields.Str(attribute='incident.severity', dump_only=True)
    incident_status = fields.Str(attribute='incident.status', dump_only=True)
    incident_category = fields.Str(attribute='incident.category.name', dump_only=True)
    incident_location = fields.Str(attribute='incident.location_text', dump_only=True)
    incident_latitude = fields.Decimal(attribute='incident.latitude', as_string=True, places=6, allow_none=True)
    incident_longitude = fields.Decimal(attribute='incident.longitude', as_string=True, places=6, allow_none=True)
    
    # Assignment info
    priority_rank = fields.Int()
    distance_km = fields.Float(allow_none=True)
    status = fields.Str()
    assigned_at = fields.DateTime()
    is_active = fields.Bool(dump_only=True)


class AssignmentDetailSchema(IncidentAssignmentSchema):
    """Extended schema with full incident details"""
    # Include full incident data
    incident = fields.Nested('IncidentReportSchema', dump_only=True)

