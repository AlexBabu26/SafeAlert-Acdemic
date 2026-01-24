"""
User schemas for SafeAlert
"""
from marshmallow import Schema, fields, validate, ValidationError, validates_schema
from app.models import User


class UserRegistrationSchema(Schema):
    """Schema for user registration"""
    username = fields.Str(required=True, validate=validate.Length(min=3, max=150))
    email = fields.Email(required=False, allow_none=True)
    first_name = fields.Str(required=False, allow_none=True, default='')
    last_name = fields.Str(required=False, allow_none=True, default='')
    password = fields.Str(required=True, validate=validate.Length(min=8), load_only=True)
    password2 = fields.Str(required=True, load_only=True)
    
    @validates_schema
    def validate_passwords(self, data, **kwargs):
        """Validate that passwords match"""
        if data.get('password') != data.get('password2'):
            raise ValidationError({'password': ['Password fields didn\'t match.']})
        
        # Basic password validation
        password = data.get('password', '')
        if len(password) < 8:
            raise ValidationError({'password': ['This password is too short. It must contain at least 8 characters.']})
        
        # Check for common passwords (simplified)
        common_passwords = ['password', '12345678', 'qwerty', 'abc123']
        if password.lower() in common_passwords:
            raise ValidationError({'password': ['This password is too common.']})


class UserSchema(Schema):
    """Schema for user serialization"""
    id = fields.Int(dump_only=True)
    username = fields.Str()
    email = fields.Email(allow_none=True)
    first_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    is_staff = fields.Bool(dump_only=True)
    is_responder = fields.Bool(dump_only=True)
    is_dispatcher = fields.Bool(dump_only=True)
    department_id = fields.Int(dump_only=True, allow_none=True)
    date_joined = fields.DateTime(dump_only=True)


