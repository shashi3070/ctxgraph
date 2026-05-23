from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Represents a registered user in the system."""

    id: str
    username: str
    email: str
    hashed_password: str
    role: str = "user"
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Serialize the user to a dictionary suitable for JSON responses."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def from_dict(data: dict) -> "User":
        """Create a User instance from a dictionary (e.g., from database)."""
        return User(
            id=data["id"],
            username=data["username"],
            email=data["email"],
            hashed_password=data["hashed_password"],
            role=data.get("role", "user"),
            is_active=data.get("is_active", True),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.utcnow()
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if data.get("updated_at")
                else None
            ),
        )
