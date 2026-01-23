"""
Notification-related schemas for SafeAlert
"""
from marshmallow import Schema, fields


class NotificationSchema(Schema):
    """Schema for Notification serialization"""
    id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    
    type = fields.Str()
    title = fields.Str()
    message = fields.Str()
    priority = fields.Str()
    
    data = fields.Dict(allow_none=True)
    action_url = fields.Str(allow_none=True)
    
    is_read = fields.Bool()
    read_at = fields.DateTime(allow_none=True)
    
    created_at = fields.DateTime(dump_only=True)
    expires_at = fields.DateTime(allow_none=True)
    is_expired = fields.Bool(dump_only=True)


class NotificationListSchema(Schema):
    """Schema for notification list (minimal fields)"""
    id = fields.Int(dump_only=True)
    type = fields.Str()
    title = fields.Str()
    message = fields.Str()
    priority = fields.Str()
    is_read = fields.Bool()
    action_url = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)

