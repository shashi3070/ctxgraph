import logging
from typing import Any, Dict, List
from . import BaseRouter
from ..services.post_service import PostService


logger = logging.getLogger(__name__)


class PostRouter(BaseRouter):
    """Route handlers for blog-post CRUD and publishing.

    Listing endpoints are public (only published posts shown to anonymous
    users).  Mutating endpoints require authentication and enforce
    author-based access control.
    """

    def __init__(self, post_service: PostService):
        super().__init__(prefix="/posts")
        self._post_service = post_service

    async def handle_get_posts(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """List posts with pagination.  Unpublished posts are visible only to admins."""
        query = request.get("query_string", {})
        try:
            skip = int(query.get("skip", 0))
            limit = min(int(query.get("limit", 50)), 200)
        except (ValueError, TypeError):
            return {"status_code": 400, "body": {"error": "Invalid pagination parameters"}}

        user = request.get("user")
        include_unpublished = bool(user and user.role == "admin") if user else False

        posts = self._post_service.get_all(
            skip=skip, limit=limit, include_unpublished=include_unpublished
        )
        return {
            "status_code": 200,
            "body": {
                "posts": [p.to_dict() for p in posts],
                "total": len(posts),
                "skip": skip,
                "limit": limit,
            },
        }

    async def handle_get_post(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get a single post by ID.  Unpublished posts return 404 for non-authors/admins."""
        post_id = request.get("path_params", {}).get("post_id", "")
        post = self._post_service.get_by_id(post_id)
        if not post:
            return {"status_code": 404, "body": {"error": f"Post {post_id} not found"}}

        if not post.published:
            user = request.get("user")
            if not user or (user.id != post.author_id and user.role != "admin"):
                return {"status_code": 404, "body": {"error": f"Post {post_id} not found"}}

        return {"status_code": 200, "body": {"post": post.to_dict()}}

    async def handle_create_post(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new blog post as the authenticated user."""
        user = request.get("user")
        if not user:
            return {"status_code": 401, "body": {"error": "Authentication required"}}

        body = request.get("body", {})
        title = body.get("title", "")
        content = body.get("content", "")

        if not title or not content:
            return {"status_code": 400, "body": {"error": "title and content are required"}}

        try:
            post = self._post_service.create(
                title=title, content=content, author_id=user.id
            )
            return {"status_code": 201, "body": {"post": post.to_dict(), "message": "Post created"}}
        except ValueError as exc:
            return {"status_code": 400, "body": {"error": str(exc)}}

    async def handle_update_post(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Update a post's title, content, or published status."""
        user = request.get("user")
        if not user:
            return {"status_code": 401, "body": {"error": "Authentication required"}}

        post_id = request.get("path_params", {}).get("post_id", "")
        updates = request.get("body", {})
        allowed_fields = {"title", "content", "published"}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered_updates:
            return {"status_code": 400, "body": {"error": "No valid fields to update"}}

        try:
            post = self._post_service.update(post_id, filtered_updates, user.id)
            if not post:
                return {"status_code": 404, "body": {"error": f"Post {post_id} not found"}}
            return {"status_code": 200, "body": {"post": post.to_dict(), "message": "Post updated"}}
        except PermissionError as exc:
            return {"status_code": 403, "body": {"error": str(exc)}}

    async def handle_delete_post(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a post.  Admins may delete any post."""
        user = request.get("user")
        if not user:
            return {"status_code": 401, "body": {"error": "Authentication required"}}

        post_id = request.get("path_params", {}).get("post_id", "")
        is_admin = user.role == "admin"

        try:
            deleted = self._post_service.delete(post_id, user.id, is_admin=is_admin)
            if not deleted:
                return {"status_code": 404, "body": {"error": f"Post {post_id} not found"}}
            return {"status_code": 200, "body": {"message": "Post deleted successfully"}}
        except PermissionError as exc:
            return {"status_code": 403, "body": {"error": str(exc)}}

    async def handle_publish_post(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Publish an unpublished post (author only)."""
        user = request.get("user")
        if not user:
            return {"status_code": 401, "body": {"error": "Authentication required"}}

        post_id = request.get("path_params", {}).get("post_id", "")
        try:
            post = self._post_service.publish_post(post_id, user.id)
            if not post:
                return {"status_code": 404, "body": {"error": f"Post {post_id} not found"}}
            return {"status_code": 200, "body": {"post": post.to_dict(), "message": "Post published"}}
        except PermissionError as exc:
            return {"status_code": 403, "body": {"error": str(exc)}}

    def register_routes(self) -> List[Dict[str, Any]]:
        return [
            {"method": "GET", "path": f"{self.prefix}", "handler": self.handle_get_posts, "auth_required": False},
            {"method": "GET", "path": f"{self.prefix}/{{post_id}}", "handler": self.handle_get_post, "auth_required": False},
            {"method": "POST", "path": f"{self.prefix}", "handler": self.handle_create_post, "auth_required": True},
            {"method": "PUT", "path": f"{self.prefix}/{{post_id}}", "handler": self.handle_update_post, "auth_required": True},
            {"method": "DELETE", "path": f"{self.prefix}/{{post_id}}", "handler": self.handle_delete_post, "auth_required": True},
            {"method": "POST", "path": f"{self.prefix}/{{post_id}}/publish", "handler": self.handle_publish_post, "auth_required": True},
        ]
