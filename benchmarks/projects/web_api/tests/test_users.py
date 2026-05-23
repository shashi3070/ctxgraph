import pytest
from services.user_service import UserService


class TestUserService:
    """Tests for user CRUD operations, uniqueness constraints, and pagination."""

    @pytest.fixture
    async def service(self):
        svc = UserService()
        await svc.initialize()
        return svc

    @pytest.mark.asyncio
    async def test_create_and_get_user(self, service):
        user = service.create("alice", "alice@example.com", "hashed_password_123")
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.role == "user"
        assert user.is_active is True

        fetched = service.get_by_id(user.id)
        assert fetched is not None
        assert fetched.id == user.id

        by_email = service.get_by_email("alice@example.com")
        assert by_email is not None
        assert by_email.id == user.id

        by_username = service.get_by_username("alice")
        assert by_username is not None
        assert by_username.id == user.id

    @pytest.mark.asyncio
    async def test_duplicate_email_raises_error(self, service):
        service.create("alice", "alice@example.com", "hash1")
        with pytest.raises(ValueError, match="already registered"):
            service.create("bob", "alice@example.com", "hash2")

    @pytest.mark.asyncio
    async def test_duplicate_username_raises_error(self, service):
        service.create("alice", "alice@example.com", "hash1")
        with pytest.raises(ValueError, match="already taken"):
            service.create("alice", "bob@example.com", "hash2")

    @pytest.mark.asyncio
    async def test_get_all_users_pagination(self, service):
        for i in range(5):
            service.create(f"user{i}", f"user{i}@test.com", "hash")
        all_users = service.get_all(skip=0, limit=10)
        assert len(all_users) == 6  # 5 created + 1 admin from initialize()

        paginated = service.get_all(skip=1, limit=2)
        assert len(paginated) == 2

    @pytest.mark.asyncio
    async def test_update_user(self, service):
        user = service.create("alice", "alice@example.com", "hash")
        updated = service.update(
            user.id,
            {"username": "alice_updated", "email": "alice.new@example.com"},
        )
        assert updated is not None
        assert updated.username == "alice_updated"
        assert updated.email == "alice.new@example.com"

        fetched = service.get_by_id(user.id)
        assert fetched.username == "alice_updated"

    @pytest.mark.asyncio
    async def test_update_nonexistent_user(self, service):
        result = service.update("bad-id", {"username": "nope"})
        assert result is None

    @pytest.mark.asyncio
    async def test_update_role(self, service):
        user = service.create("bob", "bob@example.com", "hash")
        updated = service.update(user.id, {"role": "admin"})
        assert updated.role == "admin"

    @pytest.mark.asyncio
    async def test_update_is_active(self, service):
        user = service.create("charlie", "charlie@example.com", "hash")
        updated = service.update(user.id, {"is_active": False})
        assert updated.is_active is False

    @pytest.mark.asyncio
    async def test_delete_user(self, service):
        user = service.create("alice", "alice@example.com", "hash")
        deleted = service.delete(user.id)
        assert deleted is True
        assert service.get_by_id(user.id) is None
        assert service.get_by_email("alice@example.com") is None
        assert service.get_by_username("alice") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, service):
        deleted = service.delete("nonexistent-id")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_admin_user_exists_after_init(self, service):
        admin = service.get_by_username("admin")
        assert admin is not None
        assert admin.role == "admin"
        assert admin.email == "admin@example.com"

    @pytest.mark.asyncio
    async def test_create_user_with_invalid_role_defaults_to_user(self, service):
        user = service.create("test", "test@test.com", "hash", role="superadmin")
        assert user.role == "user"
