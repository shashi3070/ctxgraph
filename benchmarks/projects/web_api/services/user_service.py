import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..models.user import User
from ..config import settings
from . import BaseService


logger = logging.getLogger(__name__)


class UserService(BaseService):
    """Business-logic layer for user management.

    Stores users in-memory (simulating a database) with uniqueness
    constraints on email and username.
    """

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._email_index: Dict[str, str] = {}
        self._username_index: Dict[str, str] = {}

    async def initialize(self) -> None:
        admin_user = User(
            id=str(uuid.uuid4()),
            username=settings.admin_default_username,
            email=settings.admin_default_email,
            hashed_password="",
            role="admin",
        )
        self._users[admin_user.id] = admin_user
        self._email_index[admin_user.email] = admin_user.id
        self._username_index[admin_user.username] = admin_user.id
        logger.info("UserService initialized with admin user %s", admin_user.username)

    async def health_check(self) -> Dict[str, Any]:
        return {
            "service": "user",
            "status": "healthy",
            "total_users": len(self._users),
        }

    def _check_unique_constraints(
        self, username: str, email: str, exclude_id: Optional[str] = None
    ) -> None:
        existing_by_email = self._email_index.get(email)
        if existing_by_email and existing_by_email != exclude_id:
            raise ValueError(f"Email '{email}' is already registered")

        existing_by_username = self._username_index.get(username)
        if existing_by_username and existing_by_username != exclude_id:
            raise ValueError(f"Username '{username}' is already taken")

    def create(
        self, username: str, email: str, hashed_password: str, role: str = "user"
    ) -> User:
        """Create a new user after validating uniqueness constraints."""
        self._check_unique_constraints(username, email)

        if role not in ("user", "admin"):
            role = "user"

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
        )
        self._users[user.id] = user
        self._email_index[user.email] = user.id
        self._username_index[user.username] = user.id
        logger.info("Created user %s (%s)", user.username, user.id)
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        user_id = self._email_index.get(email)
        return self._users.get(user_id) if user_id else None

    def get_by_username(self, username: str) -> Optional[User]:
        user_id = self._username_index.get(username)
        return self._users.get(user_id) if user_id else None

    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Return a paginated, newest-first list of users."""
        all_users = list(self._users.values())
        all_users.sort(key=lambda u: u.created_at, reverse=True)
        return all_users[skip : skip + limit]

    def update(self, user_id: str, updates: Dict[str, Any]) -> Optional[User]:
        """Update allowed fields on a user.  Returns None if not found."""
        user = self._users.get(user_id)
        if not user:
            return None

        new_username = updates.get("username", user.username)
        new_email = updates.get("email", user.email)
        self._check_unique_constraints(new_username, new_email, exclude_id=user_id)

        if new_username != user.username:
            del self._username_index[user.username]
            self._username_index[new_username] = user_id
            user.username = new_username

        if new_email != user.email:
            del self._email_index[user.email]
            self._email_index[new_email] = user_id
            user.email = new_email

        if "role" in updates and updates["role"] in ("user", "admin"):
            user.role = updates["role"]
        if "is_active" in updates:
            user.is_active = bool(updates["is_active"])
        if "hashed_password" in updates:
            user.hashed_password = updates["hashed_password"]

        user.updated_at = datetime.utcnow()
        logger.info("Updated user %s", user_id)
        return user

    def delete(self, user_id: str) -> bool:
        """Remove a user and its index entries.  Returns False if not found."""
        user = self._users.pop(user_id, None)
        if not user:
            return False
        self._email_index.pop(user.email, None)
        self._username_index.pop(user.username, None)
        logger.info("Deleted user %s (%s)", user.username, user_id)
        return True
