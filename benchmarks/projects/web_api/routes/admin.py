import logging
from typing import Any, Dict, List
from . import BaseRouter
from ..services.user_service import UserService
from ..services.post_service import PostService
from ..services.auth_service import AuthService


logger = logging.getLogger(__name__)


class AdminRouter(BaseRouter):
    """Route handlers for admin-only operations: system stats, user management,
    account deactivation, and force-deleting users with their posts."""

    def __init__(
        self,
        user_service: UserService,
        post_service: PostService,
        auth_service: AuthService,
    ):
        super().__init__(prefix="/admin")
        self._user_service = user_service
        self._post_service = post_service
        self._auth_service = auth_service

    def _require_admin(self, request: Dict[str, Any]) -> None:
        user = request.get("user")
        if not user:
            raise PermissionError("Authentication required")
        if user.role != "admin":
            raise PermissionError("Admin access required")

    async def handle_get_stats(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Return health/diagnostic stats for all services."""
        try:
            self._require_admin(request)
        except PermissionError as exc:
            return {"status_code": 403, "body": {"error": str(exc)}}

        auth_health = await self._auth_service.health_check()
        user_health = await self._user_service.health_check()
        post_health = await self._post_service.health_check()

        return {
            "status_code": 200,
            "body": {
                "services": {
                    "auth": auth_health,
                    "user": user_health,
                    "post": post_health,
                },
                "system": {"message": "Admin dashboard statistics"},
            },
        }

    async def handle_list_all_users(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """List all users with enriched data (e.g., post count)."""
        try:
            self._require_admin(request)
        except PermissionError as exc:
            return {"status_code": 403, "body": {"error": str(exc)}}

        query = request.get("query_string", {})
        try:
            skip = int(query.get("skip", 0))
            limit = min(int(query.get("limit", 500)), 1000)
        except (ValueError, TypeError):
            return {"status_code": 400, "body": {"error": "Invalid pagination parameters"}}

        users = self._user_service.get_all(skip=skip, limit=limit)
        enriched = []
        for u in users:
            user_dict = u.to_dict()
            user_dict["post_count"] = self._post_service.get_posts_count_by_author(u.id)
            enriched.append(user_dict)

        return {
            "status_code": 200,
            "body": {
                "users": enriched,
                "total": len(enriched),
                "skip": skip,
                "limit": limit,
            },
        }

    async def handle_force_delete_user(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Admin-only: delete a user and all of their posts."""
        try:
            self._require_admin(request)
        except PermissionError as exc:
            return {"status_code": 403, "body": {"error": str(exc)}}

        target_id = request.get("path_params", {}).get("user_id", "")
        admin_user = request["user"]

        if admin_user.id == target_id:
            return {"status_code": 400, "body": {"error": "Cannot delete your own admin account"}}

        target_user = self._user_service.get_by_id(target_id)
        if not target_user:
            return {"status_code": 404, "body": {"error": f"User {target_id} not found"}}

        user_posts = self._post_service.get_by_author(target_id, limit=1000)
        for post in user_posts:
            self._post_service.delete(post.id, admin_user.id, is_admin=True)

        self._user_service.delete(target_id)
        logger.info("Admin %s force-deleted user %s", admin_user.id, target_id)

        return {
            "status_code": 200,
            "body": {
                "message": f"User {target_id} and all associated posts deleted",
                "deleted_posts": len(user_posts),
            },
        }

    async def handle_deactivate_user(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Admin-only: deactivate a user account."""
        try:
            self._require_admin(request)
        except PermissionError as exc:
            return {"status_code": 403, "body": {"error": str(exc)}}

        target_id = request.get("path_params", {}).get("user_id", "")
        target_user = self._user_service.get_by_id(target_id)
        if not target_user:
            return {"status_code": 404, "body": {"error": f"User {target_id} not found"}}

        if not target_user.is_active:
            return {"status_code": 400, "body": {"error": "User account is already inactive"}}

        self._user_service.update(target_id, {"is_active": False})
        logger.info("Admin %s deactivated user %s", request["user"].id, target_id)

        return {
            "status_code": 200,
            "body": {"message": f"User {target_id} has been deactivated"},
        }

    def register_routes(self) -> List[Dict[str, Any]]:
        return [
            {"method": "GET", "path": f"{self.prefix}/stats", "handler": self.handle_get_stats, "auth_required": True},
            {"method": "GET", "path": f"{self.prefix}/users", "handler": self.handle_list_all_users, "auth_required": True},
            {"method": "DELETE", "path": f"{self.prefix}/users/{{user_id}}", "handler": self.handle_force_delete_user, "auth_required": True},
            {"method": "PUT", "path": f"{self.prefix}/users/{{user_id}}/deactivate", "handler": self.handle_deactivate_user, "auth_required": True},
        ]
