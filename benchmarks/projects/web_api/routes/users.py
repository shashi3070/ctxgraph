import logging
from typing import Any, Dict, List
from . import BaseRouter
from ..services.user_service import UserService
from ..services.auth_service import AuthService


logger = logging.getLogger(__name__)


class UserRouter(BaseRouter):
    """Route handlers for user CRUD operations.

    Most endpoints require authentication; user creation requires admin
    privileges.  Users may update their own profile; admins may update any.
    """

    def __init__(self, user_service: UserService, auth_service: AuthService):
        super().__init__(prefix="/users")
        self._user_service = user_service
        self._auth_service = auth_service

    async def handle_get_users(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """List all users with pagination."""
        query = request.get("query_string", {})
        try:
            skip = int(query.get("skip", 0))
            limit = min(int(query.get("limit", 100)), 200)
        except (ValueError, TypeError):
            return {"status_code": 400, "body": {"error": "Invalid pagination parameters"}}

        users = self._user_service.get_all(skip=skip, limit=limit)
        return {
            "status_code": 200,
            "body": {
                "users": [u.to_dict() for u in users],
                "total": len(users),
                "skip": skip,
                "limit": limit,
            },
        }

    async def handle_get_user(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get a single user by ID."""
        user_id = request.get("path_params", {}).get("user_id", "")
        user = self._user_service.get_by_id(user_id)
        if not user:
            return {"status_code": 404, "body": {"error": f"User {user_id} not found"}}
        return {"status_code": 200, "body": {"user": user.to_dict()}}

    async def handle_create_user(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Admin-only: create a new user."""
        current_user = request.get("user")
        if not current_user or current_user.role != "admin":
            return {"status_code": 403, "body": {"error": "Admin access required"}}

        body = request.get("body", {})
        username = body.get("username", "")
        email = body.get("email", "")
        password = body.get("password", "")
        role = body.get("role", "user")

        if not username or not email or not password:
            return {"status_code": 400, "body": {"error": "username, email, and password are required"}}

        hashed = self._auth_service.hash_password(password)
        try:
            user = self._user_service.create(
                username=username, email=email, hashed_password=hashed, role=role
            )
            return {"status_code": 201, "body": {"user": user.to_dict(), "message": "User created"}}
        except ValueError as exc:
            return {"status_code": 409, "body": {"error": str(exc)}}

    async def handle_update_user(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Update a user's profile.  Users may update themselves; admins may update anyone."""
        user_id = request.get("path_params", {}).get("user_id", "")
        current_user = request.get("user")

        if not current_user:
            return {"status_code": 401, "body": {"error": "Authentication required"}}
        if current_user.id != user_id and current_user.role != "admin":
            return {"status_code": 403, "body": {"error": "Cannot update another user's profile"}}

        updates = request.get("body", {})
        allowed_fields = {"username", "email", "role", "is_active"}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered_updates:
            return {"status_code": 400, "body": {"error": "No valid fields to update"}}

        user = self._user_service.update(user_id, filtered_updates)
        if not user:
            return {"status_code": 404, "body": {"error": f"User {user_id} not found"}}
        return {"status_code": 200, "body": {"user": user.to_dict(), "message": "User updated"}}

    async def handle_delete_user(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Admin-only: delete a user.  Admins cannot delete themselves."""
        user_id = request.get("path_params", {}).get("user_id", "")
        current_user = request.get("user")

        if not current_user or current_user.role != "admin":
            return {"status_code": 403, "body": {"error": "Admin access required"}}

        if current_user.id == user_id:
            return {"status_code": 400, "body": {"error": "Cannot delete your own account"}}

        deleted = self._user_service.delete(user_id)
        if not deleted:
            return {"status_code": 404, "body": {"error": f"User {user_id} not found"}}
        return {"status_code": 200, "body": {"message": "User deleted successfully"}}

    def register_routes(self) -> List[Dict[str, Any]]:
        return [
            {"method": "GET", "path": f"{self.prefix}", "handler": self.handle_get_users, "auth_required": True},
            {"method": "GET", "path": f"{self.prefix}/{{user_id}}", "handler": self.handle_get_user, "auth_required": True},
            {"method": "POST", "path": f"{self.prefix}", "handler": self.handle_create_user, "auth_required": True},
            {"method": "PUT", "path": f"{self.prefix}/{{user_id}}", "handler": self.handle_update_user, "auth_required": True},
            {"method": "DELETE", "path": f"{self.prefix}/{{user_id}}", "handler": self.handle_delete_user, "auth_required": True},
        ]
