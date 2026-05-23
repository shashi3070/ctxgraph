"""Database access layer for user service."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from shared.logging import get_logger
from shared.metrics import get_collector

from services.users.models import UserProfile, UserStatus


class UserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: uuid.UUID) -> Optional[UserProfile]:
        pass

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[UserProfile]:
        pass

    @abstractmethod
    async def find_by_username(self, username: str) -> Optional[UserProfile]:
        pass

    @abstractmethod
    async def find_all(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[UserStatus] = None
    ) -> List[UserProfile]:
        pass

    @abstractmethod
    async def create(self, user: UserProfile) -> UserProfile:
        pass

    @abstractmethod
    async def update(self, user_id: uuid.UUID, updates: Dict[str, Any]) -> Optional[UserProfile]:
        pass

    @abstractmethod
    async def delete(self, user_id: uuid.UUID) -> bool:
        pass

    @abstractmethod
    async def count(self, status: Optional[UserStatus] = None) -> int:
        pass


class InMemoryUserRepository(UserRepository):
    def __init__(self):
        self._users: Dict[uuid.UUID, UserProfile] = {}
        self._email_index: Dict[str, uuid.UUID] = {}
        self._username_index: Dict[str, uuid.UUID] = {}
        self.logger = get_logger("InMemoryUserRepository", "users-service")
        self.metrics = get_collector("users-service")

    async def find_by_id(self, user_id: uuid.UUID) -> Optional[UserProfile]:
        self.logger.debug(f"Finding user by ID: {user_id}")
        return self._users.get(user_id)

    async def find_by_email(self, email: str) -> Optional[UserProfile]:
        self.logger.debug(f"Finding user by email: {email}")
        email_lower = email.lower()
        if email_lower in self._email_index:
            return self._users.get(self._email_index[email_lower])
        return None

    async def find_by_username(self, username: str) -> Optional[UserProfile]:
        self.logger.debug(f"Finding user by username: {username}")
        username_lower = username.lower()
        if username_lower in self._username_index:
            return self._users.get(self._username_index[username_lower])
        return None

    async def find_all(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[UserStatus] = None
    ) -> List[UserProfile]:
        self.logger.debug(f"Listing users: page={page}, page_size={page_size}")

        users = list(self._users.values())

        if status:
            users = [u for u in users if u.status == status]

        users.sort(key=lambda u: u.created_at, reverse=True)

        start_index = (page - 1) * page_size
        end_index = start_index + page_size

        return users[start_index:end_index]

    async def create(self, user: UserProfile) -> UserProfile:
        self.logger.info(f"Creating user: {user.user_id}")

        if user.user_id in self._users:
            raise ValueError(f"User {user.user_id} already exists")

        self._users[user.user_id] = user

        if user.email:
            self._email_index[user.email.lower()] = user.user_id

        if user.username:
            self._username_index[user.username.lower()] = user.user_id

        self.metrics.increment_counter("repository_creates_total")

        return user

    async def update(self, user_id: uuid.UUID, updates: Dict[str, Any]) -> Optional[UserProfile]:
        self.logger.info(f"Updating user: {user_id}")

        if user_id not in self._users:
            return None

        user = self._users[user_id]

        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.utcnow()

        if "email" in updates:
            old_email = None
            for email, uid in list(self._email_index.items()):
                if uid == user_id:
                    old_email = email
                    break
            if old_email:
                del self._email_index[old_email]
            if user.email:
                self._email_index[user.email.lower()] = user_id

        if "username" in updates:
            old_username = None
            for uname, uid in list(self._username_index.items()):
                if uid == user_id:
                    old_username = uname
                    break
            if old_username:
                del self._username_index[old_username]
            if user.username:
                self._username_index[user.username.lower()] = user_id

        self.metrics.increment_counter("repository_updates_total")

        return user

    async def delete(self, user_id: uuid.UUID) -> bool:
        self.logger.info(f"Deleting user: {user_id}")

        if user_id not in self._users:
            return False

        user = self._users[user_id]

        if user.email and user.email.lower() in self._email_index:
            del self._email_index[user.email.lower()]

        if user.username and user.username.lower() in self._username_index:
            del self._username_index[user.username.lower()]

        del self._users[user_id]

        self.metrics.increment_counter("repository_deletes_total")

        return True

    async def count(self, status: Optional[UserStatus] = None) -> int:
        if status:
            return sum(1 for u in self._users.values() if u.status == status)
        return len(self._users)


class DatabaseUserRepository(UserRepository):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.logger = get_logger("DatabaseUserRepository", "users-service")
        self.metrics = get_collector("users-service")

    async def find_by_id(self, user_id: uuid.UUID) -> Optional[UserProfile]:
        self.logger.debug(f"DB: Finding user by ID: {user_id}")
        self.metrics.increment_counter("db_queries_total")
        return None

    async def find_by_email(self, email: str) -> Optional[UserProfile]:
        self.logger.debug(f"DB: Finding user by email: {email}")
        self.metrics.increment_counter("db_queries_total")
        return None

    async def find_by_username(self, username: str) -> Optional[UserProfile]:
        self.logger.debug(f"DB: Finding user by username: {username}")
        self.metrics.increment_counter("db_queries_total")
        return None

    async def find_all(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[UserStatus] = None
    ) -> List[UserProfile]:
        self.logger.debug(f"DB: Listing users")
        self.metrics.increment_counter("db_queries_total")
        return []

    async def create(self, user: UserProfile) -> UserProfile:
        self.logger.info(f"DB: Creating user: {user.user_id}")
        self.metrics.increment_counter("db_inserts_total")
        return user

    async def update(self, user_id: uuid.UUID, updates: Dict[str, Any]) -> Optional[UserProfile]:
        self.logger.info(f"DB: Updating user: {user_id}")
        self.metrics.increment_counter("db_updates_total")
        return None

    async def delete(self, user_id: uuid.UUID) -> bool:
        self.logger.info(f"DB: Deleting user: {user_id}")
        self.metrics.increment_counter("db_deletes_total")
        return False

    async def count(self, status: Optional[UserStatus] = None) -> int:
        self.metrics.increment_counter("db_queries_total")
        return 0
