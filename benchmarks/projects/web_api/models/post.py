from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Post:
    """Represents a blog post created by a user."""

    id: str
    title: str
    content: str
    author_id: str
    published: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Serialize the post to a dictionary suitable for JSON responses."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "author_id": self.author_id,
            "published": self.published,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def from_dict(data: dict) -> "Post":
        """Create a Post instance from a dictionary (e.g., from database)."""
        return Post(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            author_id=data["author_id"],
            published=data.get("published", False),
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
