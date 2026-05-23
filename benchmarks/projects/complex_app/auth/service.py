from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any, Dict, Optional, Tuple

from complex_app.auth.jwt import JWTManager
from complex_app.auth.models import Session, TokenType, User
from complex_app.shared.base import BaseService
from complex_app.shared.cache import get_cache
from complex_app.shared.config import get_config
from complex_app.shared.database import get_database
from complex_app.shared.errors import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
)


class AuthService(BaseService):
    def __init__(self, db, cache, jwt_manager: JWTManager) -> None:
        self._db = db
        self._cache = cache
        self._jwt_manager = jwt_manager

    def _validate(self, user: Optional[User] = None) -> None:
        if user is not None and not user.is_active:
            raise AuthenticationError(
                code="inactive_user", message="User account is inactive"
            )

    def _authorize(self, user: Optional[User] = None) -> None:
        if user is None:
            raise AuthenticationError(
                code="not_authenticated",
                message="Authentication required",
            )

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def authenticate(
        self, username: str, password: str
    ) -> Tuple[User, str]:
        db = get_database()
        rows = db.fetch_all(
            "SELECT * FROM users WHERE username = :username",
            {"username": username},
        )
        user_data = rows[0] if rows else None

        if not user_data:
            raise AuthenticationError(
                code="invalid_credentials",
                message="Invalid username or password",
            )

        user = User.from_dict(user_data)
        password_hash = self._hash_password(password)

        if user.password_hash != password_hash:
            raise AuthenticationError(
                code="invalid_credentials",
                message="Invalid username or password",
            )

        if not user.is_active:
            raise AuthenticationError(
                code="inactive_user", message="User account is inactive"
            )

        token_payload = {
            "sub": user.id,
            "type": TokenType.ACCESS.value,
            "roles": user.roles,
            "iat": time.time(),
        }
        token = self._jwt_manager.create_token(token_payload)

        from datetime import datetime, timezone

        user.last_login = datetime.now(timezone.utc).isoformat()

        return user, token

    def validate_token(self, token: str) -> User:
        payload = self._jwt_manager.verify_token(token)
        user_id = payload.get("sub")

        db = get_database()
        rows = db.fetch_all(
            "SELECT * FROM users WHERE id = :id", {"id": user_id}
        )
        user_data = rows[0] if rows else None

        if not user_data:
            raise NotFoundError(
                code="user_not_found", message="User not found"
            )

        user = User.from_dict(user_data)

        if not user.is_active:
            raise AuthenticationError(
                code="inactive_user", message="User account is inactive"
            )

        return user

    def create_user(
        self, username: str, email: str, password: str
    ) -> User:
        db = get_database()
        password_hash = self._hash_password(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
        )
        db.execute(
            "INSERT INTO users (id, username, email, password_hash, roles, is_active, is_verified, created_at, updated_at) VALUES (:id, :username, :email, :password_hash, :roles, :is_active, :is_verified, :created_at, :updated_at)",
            user.to_dict(),
        )
        return user

    def get_user(self, user_id: str) -> User:
        db = get_database()
        rows = db.fetch_all(
            "SELECT * FROM users WHERE id = :id", {"id": user_id}
        )
        user_data = rows[0] if rows else None

        if not user_data:
            raise NotFoundError(
                code="user_not_found", message="User not found"
            )

        return User.from_dict(user_data)

    def update_user(self, user_id: str, data: Dict[str, Any]) -> User:
        db = get_database()
        rows = db.fetch_all(
            "SELECT * FROM users WHERE id = :id", {"id": user_id}
        )
        user_data = rows[0] if rows else None

        if not user_data:
            raise NotFoundError(
                code="user_not_found", message="User not found"
            )

        user = User.from_dict(user_data)
        for key, value in data.items():
            if hasattr(user, key):
                setattr(user, key, value)

        db.execute(
            "UPDATE users SET username = :username, email = :email, password_hash = :password_hash, roles = :roles, is_active = :is_active, is_verified = :is_verified, updated_at = :updated_at WHERE id = :id",
            user.to_dict(),
        )
        return user

    def delete_user(self, user_id: str) -> None:
        db = get_database()
        rows = db.fetch_all(
            "SELECT * FROM users WHERE id = :id", {"id": user_id}
        )

        if not rows:
            raise NotFoundError(
                code="user_not_found", message="User not found"
            )

        db.execute(
            "DELETE FROM users WHERE id = :id", {"id": user_id}
        )

    def has_permission(self, user: User, permission: str) -> bool:
        for role_name in user.roles:
            db = get_database()
            rows = db.fetch_all(
                "SELECT * FROM roles WHERE name = :name",
                {"name": role_name},
            )
            role_data = rows[0] if rows else None
            if role_data and permission in role_data.get(
                "permissions", []
            ):
                return True
        return False

    def refresh_token(
        self, refresh_token: str
    ) -> Tuple[User, str]:
        payload = self._jwt_manager.verify_token(refresh_token)
        token_type = payload.get("type")

        if token_type != TokenType.REFRESH.value:
            raise AuthenticationError(
                code="invalid_token_type",
                message="Invalid token type for refresh",
            )

        user_id = payload.get("sub")
        user = self.get_user(user_id)

        if not user.is_active:
            raise AuthenticationError(
                code="inactive_user", message="User account is inactive"
            )

        new_payload = {
            "sub": user.id,
            "type": TokenType.ACCESS.value,
            "roles": user.roles,
            "iat": time.time(),
        }
        new_token = self._jwt_manager.create_token(new_payload)

        return user, new_token
