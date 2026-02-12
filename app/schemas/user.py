"""
User schemas for SafeAlert
"""
from marshmallow import Schema, fields, validate, ValidationError, validates_schema
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat
from app.models import User


class UserRegistrationSchema(Schema):
    """Schema for user registration"""
    username = fields.Str(required=True, validate=validate.Length(min=3, max=150))
    email = fields.Email(required=False, allow_none=True)
    first_name = fields.Str(required=False, allow_none=True, default='')
    last_name = fields.Str(required=False, allow_none=True, default='')
    phone_number = fields.Str(required=False, allow_none=True)
    password = fields.Str(required=True, validate=validate.Length(min=8), load_only=True)
    password2 = fields.Str(required=True, load_only=True)
    
    # Role selection - 'citizen', 'responder', or 'department'
    role = fields.Str(required=False, validate=validate.OneOf(['citizen', 'responder', 'department']), load_default='citizen')
    
    # Responder-specific fields (required if role is responder)
    department_id = fields.Int(required=False, allow_none=True)  # For responder: which department to join
    badge_number = fields.Str(required=False, allow_none=True)
    
    # Department-specific fields (required if role is department - creates a new department/office)
    department_name = fields.Str(required=False, allow_none=True)  # e.g., "Downtown Fire Station"
    department_type = fields.Str(required=False, allow_none=True)  # FIRE, POLICE, MEDICAL, etc.
    department_code = fields.Str(required=False, allow_none=True)  # e.g., "FD-01"
    
    # Location fields (for department - where the office/station is located)
    address = fields.Str(required=False, allow_none=True)
    latitude = fields.Float(required=False, allow_none=True)
    longitude = fields.Float(required=False, allow_none=True)
    
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
        
        # Validate responder-specific fields
        if data.get('role') == 'responder':
            if not data.get('department_id'):
                raise ValidationError({'department_id': ['Please select a department to join.']})
        
        # Validate department-specific fields (creating a new office/station)
        if data.get('role') == 'department':
            if not data.get('department_name'):
                raise ValidationError({'department_name': ['Department/Office name is required.']})
            if not data.get('department_type'):
                raise ValidationError({'department_type': ['Department type is required.']})
            if not data.get('latitude') or not data.get('longitude'):
                raise ValidationError({'latitude': ['Office location is required.']})

        # Validate Indian phone number format (optional field)
        phone_number = (data.get('phone_number') or '').strip()
        if phone_number:
            try:
                parsed = phonenumbers.parse(phone_number, 'IN')
            except NumberParseException:
                raise ValidationError({'phone_number': ['Enter a valid Indian phone number (e.g., +91 9876543210).']})

            if not phonenumbers.is_valid_number(parsed) or not phonenumbers.is_valid_number_for_region(parsed, 'IN'):
                raise ValidationError({'phone_number': ['Phone number must be a valid Indian number.']})

            # Store in normalized E.164 format (+91XXXXXXXXXX)
            data['phone_number'] = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)


class UserSchema(Schema):
    """Schema for user serialization"""
    id = fields.Int(dump_only=True)
    username = fields.Str()
    email = fields.Email(allow_none=True)
    first_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    is_active = fields.Bool(dump_only=True)
    is_staff = fields.Bool(dump_only=True)
    is_responder = fields.Bool(dump_only=True)
    is_department = fields.Bool(dump_only=True)
    department_id = fields.Int(dump_only=True, allow_none=True)
    date_joined = fields.DateTime(dump_only=True)


class UserAdminSchema(Schema):
    """Schema for admin user management - includes all fields"""
    id = fields.Int(dump_only=True)
    username = fields.Str()
    email = fields.Email(allow_none=True)
    first_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    phone_number = fields.Str(allow_none=True)
    is_active = fields.Bool()
    is_staff = fields.Bool()
    is_responder = fields.Bool()
    is_department = fields.Bool()
    department_id = fields.Int(allow_none=True)
    badge_number = fields.Str(allow_none=True)
    is_on_duty = fields.Bool(dump_only=True)
    is_available = fields.Bool(dump_only=True)
    date_joined = fields.DateTime(dump_only=True)
    last_login = fields.DateTime(dump_only=True, allow_none=True)
    
    # Computed fields
    role_display = fields.Str(dump_only=True)
    full_name = fields.Str(dump_only=True)


class UserUpdateSchema(Schema):
    """Schema for updating user by admin"""
    is_active = fields.Bool(required=False)
    is_staff = fields.Bool(required=False)
    is_responder = fields.Bool(required=False)
    is_department = fields.Bool(required=False)
    department_id = fields.Int(required=False, allow_none=True)
    badge_number = fields.Str(required=False, allow_none=True)


