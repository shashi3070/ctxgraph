import pytest
from services.post_service import PostService


class TestPostService:
    """Tests for blog post CRUD, publishing workflow, and author-based access control."""

    @pytest.fixture
    async def service(self):
        svc = PostService()
        await svc.initialize()
        return svc

    @pytest.mark.asyncio
    async def test_create_and_get_post(self, service):
        post = service.create("Hello World", "This is my first post", author_id="author-1")
        assert post.title == "Hello World"
        assert post.content == "This is my first post"
        assert post.author_id == "author-1"
        assert post.published is False

        fetched = service.get_by_id(post.id)
        assert fetched is not None
        assert fetched.id == post.id

    @pytest.mark.asyncio
    async def test_create_post_empty_title_raises_error(self, service):
        with pytest.raises(ValueError, match="title cannot be empty"):
            service.create("", "some content", "author-1")

    @pytest.mark.asyncio
    async def test_create_post_empty_content_raises_error(self, service):
        with pytest.raises(ValueError, match="content cannot be empty"):
            service.create("Title", "", "author-1")

    @pytest.mark.asyncio
    async def test_get_posts_by_author(self, service):
        for i in range(3):
            service.create(f"Post {i}", f"Content {i}", author_id="author-1")
        service.create("Other post", "Other content", author_id="author-2")

        author_posts = service.get_by_author("author-1")
        assert len(author_posts) == 3

        other_posts = service.get_by_author("author-2")
        assert len(other_posts) == 1

    @pytest.mark.asyncio
    async def test_get_all_posts_excludes_unpublished_by_default(self, service):
        post1 = service.create("Published", "Content", author_id="author-1")
        post2 = service.create("Unpublished", "Content", author_id="author-1")
        service.update(post1.id, {"published": True}, user_id="author-1")

        only_published = service.get_all(include_unpublished=False)
        assert len(only_published) == 1
        assert only_published[0].id == post1.id

        with_unpublished = service.get_all(include_unpublished=True)
        assert len(with_unpublished) == 2

    @pytest.mark.asyncio
    async def test_get_all_posts_pagination(self, service):
        for i in range(5):
            p = service.create(f"Post {i}", f"Content {i}", author_id="author-1")
            service.update(p.id, {"published": True}, user_id="author-1")
        posts = service.get_all(skip=1, limit=2)
        assert len(posts) == 2

    @pytest.mark.asyncio
    async def test_update_post(self, service):
        post = service.create("Original Title", "Original content", author_id="author-1")
        updated = service.update(
            post.id,
            {"title": "Updated Title", "content": "Updated content"},
            user_id="author-1",
        )
        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.content == "Updated content"

    @pytest.mark.asyncio
    async def test_update_nonexistent_post(self, service):
        result = service.update("bad-id", {"title": "Nope"}, user_id="author-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_post_by_non_author_raises_error(self, service):
        post = service.create("My Post", "My content", author_id="author-1")
        with pytest.raises(PermissionError, match="Only the author"):
            service.update(post.id, {"title": "Hacked"}, user_id="author-2")

    @pytest.mark.asyncio
    async def test_delete_post(self, service):
        post = service.create("To delete", "Content", author_id="author-1")
        deleted = service.delete(post.id, user_id="author-1")
        assert deleted is True
        assert service.get_by_id(post.id) is None

    @pytest.mark.asyncio
    async def test_delete_post_by_admin(self, service):
        post = service.create("To delete", "Content", author_id="author-1")
        deleted = service.delete(post.id, user_id="admin-1", is_admin=True)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_post_by_non_author_raises_error(self, service):
        post = service.create("My Post", "Content", author_id="author-1")
        with pytest.raises(PermissionError, match="Only the author"):
            service.delete(post.id, user_id="author-2")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_post(self, service):
        result = service.delete("bad-id", user_id="author-1")
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_post(self, service):
        post = service.create("Draft", "Content", author_id="author-1")
        published = service.publish_post(post.id, user_id="author-1")
        assert published is not None
        assert published.published is True
        assert published.updated_at is not None

    @pytest.mark.asyncio
    async def test_publish_nonexistent_post(self, service):
        result = service.publish_post("bad-id", user_id="author-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_publish_post_by_non_author_raises_error(self, service):
        post = service.create("Draft", "Content", author_id="author-1")
        with pytest.raises(PermissionError, match="Only the author"):
            service.publish_post(post.id, user_id="author-2")

    @pytest.mark.asyncio
    async def test_get_posts_count_by_author(self, service):
        for i in range(4):
            service.create(f"Post {i}", f"Content {i}", author_id="author-1")
        count = service.get_posts_count_by_author("author-1")
        assert count == 4
        assert service.get_posts_count_by_author("nonexistent") == 0

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        health = await service.health_check()
        assert health["service"] == "post"
        assert health["status"] == "healthy"
