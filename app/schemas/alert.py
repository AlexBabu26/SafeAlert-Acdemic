"""
Alert-related schemas for SafeAlert
"""
from marshmallow import Schema, fields, validate


class SafetyAlertSchema(Schema):
    """Schema for SafetyAlert serialization"""
    id = fields.Int(dump_only=True)
    
    title = fields.Str()
    message = fields.Str()
    alert_type = fields.Str()
    severity = fields.Str()
    instructions = fields.Str(allow_none=True)
    
    center_lat = fields.Decimal(as_string=True, places=6, allow_none=True)
    center_lng = fields.Decimal(as_string=True, places=6, allow_none=True)
    radius_km = fields.Float(allow_none=True)
    is_citywide = fields.Bool()
    
    incident_id = fields.Int(allow_none=True)
    
    active_from = fields.DateTime()
    active_until = fields.DateTime(allow_none=True)
    is_active = fields.Bool()
    is_currently_active = fields.Bool(dump_only=True)
    
    push_sent_count = fields.Int(dump_only=True)
    
    created_by_id = fields.Int(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class SafetyAlertCreateSchema(Schema):
    """Schema for creating a SafetyAlert"""
    title = fields.Str(required=True, validate=validate.Length(min=5, max=200))
    message = fields.Str(required=True, validate=validate.Length(min=10))
    alert_type = fields.Str(missing='PUBLIC_SAFETY', validate=validate.OneOf([
        'INCIDENT_AREA', 'WEATHER', 'EVACUATION', 'ROAD_CLOSURE', 'PUBLIC_SAFETY', 'SYSTEM'
    ]))
    severity = fields.Str(missing='INFO', validate=validate.OneOf(['INFO', 'WARNING', 'CRITICAL']))
    instructions = fields.Str(allow_none=True)
    
    center_lat = fields.Decimal(as_string=True, places=6, allow_none=True)
    center_lng = fields.Decimal(as_string=True, places=6, allow_none=True)
    radius_km = fields.Float(allow_none=True)
    is_citywide = fields.Bool(missing=False)
    
    incident_id = fields.Int(allow_none=True)
    
    active_until = fields.DateTime(allow_none=True)


class SafetyAlertListSchema(Schema):
    """Schema for alert list (minimal fields)"""
    id = fields.Int(dump_only=True)
    title = fields.Str()
    severity = fields.Str()
    alert_type = fields.Str()
    is_active = fields.Bool()
    is_currently_active = fields.Bool(dump_only=True)
    active_from = fields.DateTime()
    active_until = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(dump_only=True)

