"""User model."""
from src.core.exceptions import ValidationError
from src.core.validators import validate_email


class User:
    def __init__(self, user_id, email, role="user"):
        self.user_id = user_id
        self.email = validate_email(email)
        self.role = role
        self._is_active = True

    def to_dict(self):
        return {
            "id": self.user_id,
            "email": self.email,
            "role": self.role,
            "active": self._is_active,
        }

    def deactivate(self):
        self._is_active = False


class AdminUser(User):
    def __init__(self, user_id, email):
        super().__init__(user_id, email, role="admin")
        self.permissions = ["read", "write", "delete", "manage_users"]

    def to_dict(self):
        base = super().to_dict()
        base["permissions"] = self.permissions
        return base
