"""
Department-related schemas for SafeAlert
"""
from marshmallow import Schema, fields, validate, validates
from app.utils.validators import validate_phone_number, validate_latitude, validate_longitude


class DepartmentSchema(Schema):
    """Schema for Department serialization"""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    code = fields.Str()
    type = fields.Str()
    description = fields.Str(allow_none=True)
    
    headquarters_lat = fields.Decimal(as_string=True, places=6)
    headquarters_lng = fields.Decimal(as_string=True, places=6)
    address = fields.Str(allow_none=True)
    coverage_radius_km = fields.Float()
    
    max_concurrent_incidents = fields.Int()
    current_active_incidents = fields.Int(dump_only=True)
    available_capacity = fields.Int(dump_only=True)
    utilization_rate = fields.Float(dump_only=True)
    
    dispatch_phone = fields.Str(allow_none=True)
    dispatch_email = fields.Email(allow_none=True)
    
    is_24_7 = fields.Bool()
    is_active = fields.Bool()
    
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class DepartmentCreateSchema(Schema):
    """Schema for creating a Department"""
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    code = fields.Str(required=True, validate=validate.Length(min=2, max=20))
    type = fields.Str(required=True, validate=validate.OneOf(['FIRE', 'POLICE', 'MEDICAL', 'RESCUE', 'HAZMAT', 'TRAFFIC']))
    description = fields.Str(allow_none=True)
    
    headquarters_lat = fields.Decimal(required=True, as_string=True, places=6)
    headquarters_lng = fields.Decimal(required=True, as_string=True, places=6)
    address = fields.Str(allow_none=True)
    coverage_radius_km = fields.Float(missing=15.0)
    
    max_concurrent_incidents = fields.Int(missing=5)
    
    dispatch_phone = fields.Str(allow_none=True)
    dispatch_email = fields.Email(allow_none=True)

    is_24_7 = fields.Bool(missing=True)

    @validates('dispatch_phone')
    def validate_dispatch_phone(self, value):
        if value:
            return validate_phone_number(value)

    @validates('headquarters_lat')
    def validate_lat(self, value):
        if value is not None:
            validate_latitude(value)

    @validates('headquarters_lng')
    def validate_lng(self, value):
        if value is not None:
            validate_longitude(value)


class DepartmentListSchema(Schema):
    """Schema for Department list (minimal fields)"""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    code = fields.Str()
    type = fields.Str()
    is_active = fields.Bool()
    current_active_incidents = fields.Int()
    available_capacity = fields.Int()


class ResourceSchema(Schema):
    """Schema for Resource serialization"""
    id = fields.Int(dump_only=True)
    department_id = fields.Int()
    type = fields.Str()
    name = fields.Str()
    identifier = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    
    status = fields.Str()
    current_incident_id = fields.Int(allow_none=True)
    
    current_lat = fields.Decimal(as_string=True, places=6, allow_none=True)
    current_lng = fields.Decimal(as_string=True, places=6, allow_none=True)
    last_location_update = fields.DateTime(allow_none=True)
    
    capacity = fields.Int(allow_none=True)
    
    created_at = fields.DateTime(dump_only=True)


class ResourceCreateSchema(Schema):
    """Schema for creating a Resource"""
    department_id = fields.Int(required=True)
    type = fields.Str(required=True, validate=validate.OneOf(['VEHICLE', 'EQUIPMENT', 'PERSONNEL']))
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    identifier = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    capacity = fields.Int(allow_none=True)

