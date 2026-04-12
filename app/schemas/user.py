"""
User schemas for SafeAlert
"""
import re
from marshmallow import Schema, fields, validate, ValidationError, validates, validates_schema
from app.utils.validators import validate_phone_number, validate_password_strength

# Allows letters (including accented/unicode), spaces, hyphens, apostrophes
_NAME_RE = re.compile(r"^[\w'\- ]+$", re.UNICODE)

def validate_name(value: str) -> None:
    """Reject names that contain digits or special characters."""
    if not value or not value.strip():
        return  # optional field — blank is fine
    if any(c.isdigit() for c in value):
        raise ValidationError('Name must not contain numbers.')
    if not _NAME_RE.match(value.strip()):
        raise ValidationError('Name may only contain letters, spaces, hyphens, and apostrophes.')


class UserRegistrationSchema(Schema):
    """Schema for user registration"""
    username    = fields.Str(required=True, validate=validate.Length(min=3, max=150))
    email       = fields.Email(required=False, allow_none=True)
    first_name  = fields.Str(required=False, allow_none=True, load_default='',
                             validate=[validate.Length(max=50), validate_name])
    last_name   = fields.Str(required=False, allow_none=True, load_default='',
                             validate=[validate.Length(max=50), validate_name])
    phone_number = fields.Str(required=False, allow_none=True)
    password    = fields.Str(required=True, validate=validate.Length(min=8), load_only=True)
    password2   = fields.Str(required=True, load_only=True)

    # Role selection
    role = fields.Str(
        required=False,
        validate=validate.OneOf(['citizen', 'responder', 'department']),
        load_default='citizen',
    )

    # Responder-specific
    department_id = fields.Int(required=False, allow_none=True)
    badge_number  = fields.Str(required=False, allow_none=True)

    # Department-specific
    department_name = fields.Str(required=False, allow_none=True)
    department_type = fields.Str(required=False, allow_none=True)
    department_code = fields.Str(required=False, allow_none=True)

    # Location (for department role)
    address   = fields.Str(required=False, allow_none=True)
    latitude  = fields.Float(required=False, allow_none=True)
    longitude = fields.Float(required=False, allow_none=True)

    @validates('phone_number')
    def validate_phone(self, value):
        if value:
            normalised = validate_phone_number(value)   # international E.164
            return normalised

    @validates_schema
    def validate_cross_fields(self, data, **kwargs):
        # ── Password strength ──
        password = data.get('password', '')
        try:
            validate_password_strength(password)
        except ValidationError as e:
            raise ValidationError({'password': e.messages})

        if data.get('password') != data.get('password2'):
            raise ValidationError({'password': ["Password fields didn't match."]})

        # ── Role-specific requirements ──
        role = data.get('role')
        if role == 'responder':
            if not data.get('department_id'):
                raise ValidationError({'department_id': ['Please select a department to join.']})

        if role == 'department':
            if not data.get('department_name'):
                raise ValidationError({'department_name': ['Department/Office name is required.']})
            if not data.get('department_type'):
                raise ValidationError({'department_type': ['Department type is required.']})
            lat = data.get('latitude')
            lng = data.get('longitude')
            if lat is None or lng is None:
                raise ValidationError({'latitude': ['Office location is required.']})
            if not (-90.0 <= float(lat) <= 90.0):
                raise ValidationError({'latitude': ['Latitude must be between -90 and 90.']})
            if not (-180.0 <= float(lng) <= 180.0):
                raise ValidationError({'longitude': ['Longitude must be between -180 and 180.']})

        # ── Phone normalisation (post-validation store) ──
        phone = (data.get('phone_number') or '').strip()
        if phone:
            data['phone_number'] = validate_phone_number(phone)


class UserSchema(Schema):
    """Schema for user serialization"""
    id           = fields.Int(dump_only=True)
    username     = fields.Str()
    email        = fields.Email(allow_none=True)
    first_name   = fields.Str(allow_none=True)
    last_name    = fields.Str(allow_none=True)
    is_active    = fields.Bool(dump_only=True)
    is_staff     = fields.Bool(dump_only=True)
    is_responder = fields.Bool(dump_only=True)
    is_department = fields.Bool(dump_only=True)
    department_id = fields.Int(dump_only=True, allow_none=True)
    date_joined  = fields.DateTime(dump_only=True)


class UserAdminSchema(Schema):
    """Schema for admin user management — includes all fields"""
    id           = fields.Int(dump_only=True)
    username     = fields.Str()
    email        = fields.Email(allow_none=True)
    first_name   = fields.Str(allow_none=True)
    last_name    = fields.Str(allow_none=True)
    phone_number = fields.Str(allow_none=True)
    is_active    = fields.Bool()
    is_staff     = fields.Bool()
    is_responder = fields.Bool()
    is_department = fields.Bool()
    department_id = fields.Int(allow_none=True)
    badge_number = fields.Str(allow_none=True)
    is_on_duty   = fields.Bool(dump_only=True)
    is_available = fields.Bool(dump_only=True)
    date_joined  = fields.DateTime(dump_only=True)
    last_login   = fields.DateTime(dump_only=True, allow_none=True)

    # Computed
    role_display = fields.Str(dump_only=True)
    full_name    = fields.Str(dump_only=True)


class UserUpdateSchema(Schema):
    """Schema for updating a user by admin"""
    is_active    = fields.Bool(required=False)
    is_staff     = fields.Bool(required=False)
    is_responder = fields.Bool(required=False)
    is_department = fields.Bool(required=False)
    department_id = fields.Int(required=False, allow_none=True)
    badge_number = fields.Str(required=False, allow_none=True, validate=validate.Length(max=50))
    phone_number = fields.Str(required=False, allow_none=True)

    @validates('phone_number')
    def validate_phone(self, value):
        if value:
            return validate_phone_number(value)
