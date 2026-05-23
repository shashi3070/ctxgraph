import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..models.post import Post
from . import BaseService


logger = logging.getLogger(__name__)


class PostService(BaseService):
    """Business-logic layer for blog post management.

    Supports CRUD, publishing workflow, author-based access control, and
    paginated listing with an optional unpublished-posts filter.
    """

    def __init__(self):
        self._posts: Dict[str, Post] = {}
        self._author_index: Dict[str, List[str]] = {}

    async def initialize(self) -> None:
        logger.info("PostService initialized")

    async def health_check(self) -> Dict[str, Any]:
        total = len(self._posts)
        published = sum(1 for p in self._posts.values() if p.published)
        return {
            "service": "post",
            "status": "healthy",
            "total_posts": total,
            "published_posts": published,
        }

    def _index_post(self, post: Post) -> None:
        self._author_index.setdefault(post.author_id, []).append(post.id)

    def _deindex_post(self, post: Post) -> None:
        ids = self._author_index.get(post.author_id, [])
        if post.id in ids:
            ids.remove(post.id)

    def create(self, title: str, content: str, author_id: str) -> Post:
        """Create a new post after basic validation."""
        if not title.strip():
            raise ValueError("Post title cannot be empty")
        if not content.strip():
            raise ValueError("Post content cannot be empty")

        post = Post(
            id=str(uuid.uuid4()),
            title=title.strip(),
            content=content.strip(),
            author_id=author_id,
        )
        self._posts[post.id] = post
        self._index_post(post)
        logger.info("Created post %s by author %s", post.id, author_id)
        return post

    def get_by_id(self, post_id: str) -> Optional[Post]:
        return self._posts.get(post_id)

    def get_by_author(
        self, author_id: str, skip: int = 0, limit: int = 50
    ) -> List[Post]:
        """Return posts by a specific author, newest first."""
        post_ids = self._author_index.get(author_id, [])
        posts = [self._posts[pid] for pid in post_ids if pid in self._posts]
        posts.sort(key=lambda p: p.created_at, reverse=True)
        return posts[skip : skip + limit]

    def get_all(
        self, skip: int = 0, limit: int = 50, include_unpublished: bool = False
    ) -> List[Post]:
        """Return a paginated list of posts, newest first.

        By default only published posts are returned; pass
        *include_unpublished=True* to include drafts.
        """
        all_posts = list(self._posts.values())
        if not include_unpublished:
            all_posts = [p for p in all_posts if p.published]
        all_posts.sort(key=lambda p: p.created_at, reverse=True)
        return all_posts[skip : skip + limit]

    def update(
        self, post_id: str, updates: Dict[str, Any], user_id: str
    ) -> Optional[Post]:
        """Update a post's title, content, or published status.

        Only the author may update the post.
        """
        post = self._posts.get(post_id)
        if not post:
            return None
        if post.author_id != user_id:
            raise PermissionError("Only the author can update this post")

        if "title" in updates and updates["title"].strip():
            post.title = updates["title"].strip()
        if "content" in updates and updates["content"].strip():
            post.content = updates["content"].strip()
        if "published" in updates:
            post.published = bool(updates["published"])

        post.updated_at = datetime.utcnow()
        logger.info("Updated post %s", post_id)
        return post

    def delete(self, post_id: str, user_id: str, is_admin: bool = False) -> bool:
        """Delete a post.  The author, or an admin when *is_admin* is True, may delete."""
        post = self._posts.get(post_id)
        if not post:
            return False
        if post.author_id != user_id and not is_admin:
            raise PermissionError("Only the author or an admin can delete this post")

        del self._posts[post_id]
        self._deindex_post(post)
        logger.info("Deleted post %s", post_id)
        return True

    def publish_post(self, post_id: str, user_id: str) -> Optional[Post]:
        """Publish a post.  Only the author may publish."""
        post = self._posts.get(post_id)
        if not post:
            return None
        if post.author_id != user_id:
            raise PermissionError("Only the author can publish this post")

        post.published = True
        post.updated_at = datetime.utcnow()
        logger.info("Published post %s", post_id)
        return post

    def get_posts_count_by_author(self, author_id: str) -> int:
        """Return the total number of posts authored by *author_id*."""
        return len(self._author_index.get(author_id, []))
