"""
Shared validation helpers for SafeAlert schemas and API endpoints.
"""
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat
from marshmallow import ValidationError
from decimal import Decimal


# ── Password ──────────────────────────────────────────────────────────────────

COMMON_PASSWORDS = {
    'password', 'password1', '12345678', '123456789', 'qwerty123',
    'qwertyui', 'abc12345', 'abc123456', 'iloveyou', 'admin123',
    'letmein1', 'welcome1', 'monkey123', 'dragon123',
}


def validate_password_strength(password: str) -> None:
    """
    Raise ValidationError if password does not meet strength requirements.
    Rules (matching registration):
      - min 8 characters
      - not in common-password list
      - must contain at least one letter and one digit
    """
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')
    if password.lower() in COMMON_PASSWORDS:
        raise ValidationError('This password is too common. Please choose a stronger password.')
    has_letter = any(c.isalpha() for c in password)
    has_digit  = any(c.isdigit() for c in password)
    if not has_letter or not has_digit:
        raise ValidationError('Password must contain at least one letter and one digit.')


# ── Phone number ──────────────────────────────────────────────────────────────

def validate_phone_number(value: str, default_region: str | None = 'IN') -> str:
    """
    Validate and normalise an Indian phone number to E.164 format using the
    Google libphonenumber library.

    • Accepts national format  (9876543210)
    • Accepts international format (+91 9876543210)
    • Returns the E.164 normalised string (e.g. '+919876543210')
    • Raises marshmallow.ValidationError on invalid input.
    """
    value = (value or '').strip()
    if not value:
        return value

    try:
        parsed = phonenumbers.parse(value, default_region)
    except NumberParseException:
        raise ValidationError(
            'Enter a valid Indian phone number (e.g. +91 9876543210 or 9876543210).'
        )

    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError('The phone number entered is not valid.')

    if not phonenumbers.is_valid_number_for_region(parsed, 'IN'):
        raise ValidationError('Phone number must be a valid Indian number.')

    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)


# ── Geographic coordinates ────────────────────────────────────────────────────

def validate_latitude(value) -> None:
    """Raise ValidationError if latitude is outside [-90, 90]."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        raise ValidationError('Latitude must be a number.')
    if not (-90.0 <= f <= 90.0):
        raise ValidationError('Latitude must be between -90 and 90.')


def validate_longitude(value) -> None:
    """Raise ValidationError if longitude is outside [-180, 180]."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        raise ValidationError('Longitude must be a number.')
    if not (-180.0 <= f <= 180.0):
        raise ValidationError('Longitude must be between -180 and 180.')


# ── Text helpers ──────────────────────────────────────────────────────────────

def non_blank(value: str) -> str:
    """Raise ValidationError if the string is blank/whitespace-only."""
    if not value or not value.strip():
        raise ValidationError('This field may not be blank.')
    return value.strip()
