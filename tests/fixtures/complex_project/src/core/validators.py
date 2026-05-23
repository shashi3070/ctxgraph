"""Validation utilities."""
from src.core.exceptions import ValidationError


def validate_port(port):
    if not 0 < port < 65536:
        raise ValidationError(f"Invalid port: {port}")


def validate_url(url):
    if not url.startswith(("redis://", "sqlite://", "postgresql://")):
        raise ValidationError(f"Invalid URL scheme: {url}")


def validate_email(email):
    if "@" not in email:
        raise ValidationError(f"Invalid email: {email}")
    return email.lower()


def validate_token(token):
    if not token or len(token) < 10:
        raise ValidationError("Token too short")
    return token
