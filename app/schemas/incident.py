"""
Incident-related schemas for SafeAlert
"""
from marshmallow import Schema, fields, validate, ValidationError
from decimal import Decimal


class CategorySchema(Schema):
    """Schema for Category"""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    description = fields.Str(allow_none=True)
    icon = fields.Str(allow_none=True)
    color = fields.Str(allow_none=True)
    default_severity = fields.Str()
    is_active = fields.Bool()
    priority_order = fields.Int()


class CategoryDepartmentMappingSchema(Schema):
    """Schema for CategoryDepartmentMapping"""
    id = fields.Int(dump_only=True)
    category_id = fields.Int()
    department_type = fields.Str()
    priority = fields.Int()
    is_required = fields.Bool()


class IncidentAttachmentSchema(Schema):
    """Schema for IncidentAttachment"""
    id = fields.Int(dump_only=True)
    file = fields.Method('get_file_url', dump_only=True)
    uploaded_at = fields.DateTime(dump_only=True)
    
    def get_file_url(self, obj):
        """Generate full URL for the attachment file"""
        if obj.file_path:
            normalized_path = str(obj.file_path).replace('\\', '/')
            return f"/media/{normalized_path}"
        return None


class IncidentMediaSchema(Schema):
    """Schema for IncidentMedia"""
    id = fields.Int(dump_only=True)
    file = fields.Method('get_file_url', dump_only=True)
    media_type = fields.Str()
    mime_type = fields.Str(allow_none=True)
    file_size_bytes = fields.Int(allow_none=True)
    duration_seconds = fields.Int(allow_none=True)
    thumbnail = fields.Method('get_thumbnail_url', dump_only=True)
    
    captured_at = fields.DateTime(allow_none=True)
    captured_latitude = fields.Decimal(as_string=True, places=6, allow_none=True)
    captured_longitude = fields.Decimal(as_string=True, places=6, allow_none=True)
    
    uploaded_at = fields.DateTime(dump_only=True)
    
    def get_file_url(self, obj):
        if obj.file_path:
            normalized_path = str(obj.file_path).replace('\\', '/')
            return f"/media/{normalized_path}"
        return None
    
    def get_thumbnail_url(self, obj):
        if obj.thumbnail_path:
            normalized_path = str(obj.thumbnail_path).replace('\\', '/')
            return f"/media/{normalized_path}"
        return None


class StatusHistorySchema(Schema):
    """Schema for StatusHistory"""
    id = fields.Int(dump_only=True)
    old_status = fields.Str(allow_none=True)
    new_status = fields.Str()
    changed_by_username = fields.Str(attribute='changed_by_user.username', dump_only=True)
    changed_at = fields.DateTime(dump_only=True)
    notes = fields.Str(allow_none=True)
    source = fields.Str(allow_none=True)


class IncidentReportSchema(Schema):
    """Schema for IncidentReport with nested relationships"""
    id = fields.Int(dump_only=True)
    
    # Reporter info
    user = fields.Int(attribute='user_id', dump_only=True)
    user_username = fields.Method('get_user_username', dump_only=True)
    is_anonymous = fields.Bool(dump_only=True)
    anonymous_tracking_code = fields.Str(dump_only=True)
    
    # Classification
    category = fields.Int(attribute='category_id')
    category_name = fields.Str(attribute='category.name', dump_only=True)
    severity = fields.Str()
    
    # Content
    title = fields.Str(allow_none=True)
    description = fields.Str()
    
    # Location
    location_text = fields.Str(allow_none=True)
    address_formatted = fields.Str(allow_none=True)
    landmark_description = fields.Str(allow_none=True)
    latitude = fields.Decimal(allow_none=True, as_string=True, places=6)
    longitude = fields.Decimal(allow_none=True, as_string=True, places=6)
    map_url = fields.Method('get_map_url', dump_only=True)
    
    # Status
    status = fields.Str(dump_only=True)
    is_verified = fields.Bool(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    
    # SLA timestamps
    created_at = fields.DateTime(dump_only=True)
    dispatch_time = fields.DateTime(allow_none=True, dump_only=True)
    acknowledge_time = fields.DateTime(allow_none=True, dump_only=True)
    arrival_time = fields.DateTime(allow_none=True, dump_only=True)
    resolution_time = fields.DateTime(allow_none=True, dump_only=True)
    
    # Response metrics
    dispatch_response_seconds = fields.Int(allow_none=True, dump_only=True)
    total_response_seconds = fields.Int(allow_none=True, dump_only=True)
    resolution_seconds = fields.Int(allow_none=True, dump_only=True)
    sla_target_minutes = fields.Int(allow_none=True, dump_only=True)
    is_sla_breached = fields.Bool(dump_only=True)
    
    # Impact
    estimated_affected_people = fields.Int(allow_none=True)
    requires_evacuation = fields.Bool()
    
    # Follow-up
    follow_up_required = fields.Bool()
    follow_up_notes = fields.Str(allow_none=True)
    
    # Metadata
    source = fields.Str(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Nested relationships
    attachments = fields.Nested(IncidentAttachmentSchema, many=True, dump_only=True)
    media = fields.Nested(IncidentMediaSchema, many=True, dump_only=True)
    status_history = fields.Nested(StatusHistorySchema, many=True, dump_only=True)
    
    def get_map_url(self, obj):
        """Generate Google Maps URL if coordinates are available"""
        if obj.latitude and obj.longitude:
            return f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
        return None
    
    def get_user_username(self, obj):
        """Get username, hiding for anonymous reports"""
        if obj.is_anonymous:
            return 'Anonymous'
        if obj.user:
            return obj.user.username
        return None


class IncidentReportCreateSchema(Schema):
    """Schema for creating IncidentReport"""
    category = fields.Int(required=True, data_key='category', load_only=True)
    severity = fields.Str(required=False, missing='MEDIUM', validate=validate.OneOf([
        'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'
    ]))
    title = fields.Str(required=False, allow_none=True, default='')
    description = fields.Str(required=True)
    location_text = fields.Str(required=False, allow_none=True, default='')
    address_formatted = fields.Str(required=False, allow_none=True)
    landmark_description = fields.Str(required=False, allow_none=True)
    latitude = fields.Decimal(required=False, allow_none=True, as_string=True, places=6)
    longitude = fields.Decimal(required=False, allow_none=True, as_string=True, places=6)
    
    # Optional fields
    estimated_affected_people = fields.Int(required=False, allow_none=True)
    requires_evacuation = fields.Bool(required=False, missing=False)
    
    # For anonymous reporting
    is_anonymous = fields.Bool(required=False, missing=False)


class IncidentQuickReportSchema(Schema):
    """Schema for quick/panic report (minimal data)"""
    category = fields.Int(required=False, allow_none=True)  # Optional, defaults to "Emergency"
    severity = fields.Str(required=False, missing='CRITICAL')
    latitude = fields.Decimal(required=True, as_string=True, places=6)
    longitude = fields.Decimal(required=True, as_string=True, places=6)
    description = fields.Str(required=False, missing='Quick emergency report')


class IncidentStatusUpdateSchema(Schema):
    """Schema for updating incident status"""
    status = fields.Str(required=True, validate=validate.OneOf([
        'REPORTED', 'VERIFIED', 'DISPATCHED', 'ACKNOWLEDGED', 
        'EN_ROUTE', 'ON_SCENE', 'RESOLVED', 'CLOSED', 'CANCELLED'
    ]))
    notes = fields.Str(required=False, allow_none=True, default='')


class IncidentListSchema(Schema):
    """Schema for incident list (minimal fields for dashboard)"""
    id = fields.Int(dump_only=True)
    title = fields.Str()
    category_name = fields.Str(attribute='category.name', dump_only=True)
    severity = fields.Str()
    status = fields.Str()
    location_text = fields.Str(allow_none=True)
    latitude = fields.Decimal(allow_none=True, as_string=True, places=6)
    longitude = fields.Decimal(allow_none=True, as_string=True, places=6)
    created_at = fields.DateTime(dump_only=True)
    is_sla_breached = fields.Bool(dump_only=True)
    is_anonymous = fields.Bool()
