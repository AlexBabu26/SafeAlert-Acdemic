"""
Message schemas for SafeAlert
"""
from marshmallow import Schema, fields, validate, validates
from app.utils.validators import non_blank


class IncidentMessageSchema(Schema):
    """Schema for IncidentMessage"""
    id               = fields.Int(dump_only=True)
    incident         = fields.Int(attribute='incident_id', dump_only=True)
    sender           = fields.Int(attribute='sender_id', dump_only=True)
    sender_username  = fields.Str(attribute='sender.username', dump_only=True)
    sender_role      = fields.Str(dump_only=True)
    message          = fields.Str()
    created_at       = fields.DateTime(dump_only=True)


class IncidentMessageCreateSchema(Schema):
    """Schema for creating IncidentMessage"""
    message = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=2000),
    )

    @validates('message')
    def validate_message(self, value):
        non_blank(value)
