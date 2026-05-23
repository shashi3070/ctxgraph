import pytest
from services.auth_service import AuthService
from services.user_service import UserService


class TestAuthService:
    """Tests for password hashing, JWT creation/validation, and session management."""

    @pytest.fixture
    def services(self):
        user_service = UserService()
        auth_service = AuthService(user_service=user_service)
        return user_service, auth_service

    @pytest.mark.asyncio
    async def test_password_hashing_and_verification(self, services):
        _, auth_service = services
        password = "SuperSecureP@ss1"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password(password, hashed) is True
        assert auth_service.verify_password("WrongPassword", hashed) is False

    @pytest.mark.asyncio
    async def test_jwt_token_creation_and_decoding(self, services):
        _, auth_service = services
        user_id = "user-123"
        token = auth_service.create_jwt(user_id, {"role": "admin"})
        payload = auth_service.decode_jwt(token)
        assert payload["sub"] == user_id
        assert payload["role"] == "admin"
        assert "exp" in payload
        assert "jti" in payload

    @pytest.mark.asyncio
    async def test_invalid_jwt_signature_rejected(self, services):
        _, auth_service = services
        token = auth_service.create_jwt("user-1")
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.invalidsignature"
        with pytest.raises(ValueError, match="Invalid JWT signature"):
            auth_service.decode_jwt(tampered)

    @pytest.mark.asyncio
    async def test_malformed_jwt_rejected(self, services):
        _, auth_service = services
        with pytest.raises(ValueError, match="must have exactly 3 parts"):
            auth_service.decode_jwt("not.a.jwt")

    @pytest.mark.asyncio
    async def test_session_creation_and_validation(self, services):
        user_service, auth_service = services
        await user_service.initialize()
        user = user_service.create(
            "testuser", "test@test.com", auth_service.hash_password("pass")
        )
        session = auth_service.create_session(user.id)
        assert session.user_id == user.id
        assert session.is_valid is True

        validated = auth_service.validate_session(session.token)
        assert validated is not None
        assert validated.user_id == user.id

    @pytest.mark.asyncio
    async def test_session_invalidation(self, services):
        user_service, auth_service = services
        await user_service.initialize()
        user = user_service.create(
            "testuser2", "test2@test.com", auth_service.hash_password("pass")
        )
        session = auth_service.create_session(user.id)
        auth_service.invalidate_session(session.token)

        validated = auth_service.validate_session(session.token)
        assert validated is None

    @pytest.mark.asyncio
    async def test_multiple_sessions_for_same_user(self, services):
        user_service, auth_service = services
        await user_service.initialize()
        user = user_service.create(
            "multi", "multi@test.com", auth_service.hash_password("pass")
        )
        s1 = auth_service.create_session(user.id)
        s2 = auth_service.create_session(user.id)
        assert s1.token != s2.token

        assert auth_service.validate_session(s1.token) is not None
        assert auth_service.validate_session(s2.token) is not None

    @pytest.mark.asyncio
    async def test_password_hash_format(self, services):
        _, auth_service = services
        hashed = auth_service.hash_password("mypassword")
        assert "$" in hashed
        salt, hash_hex = hashed.split("$")
        assert len(salt) == 32
        assert len(hash_hex) == 64
