"""Auth tests."""
from src.services.auth import AuthService


class TestAuthService:
    def test_login_success(self):
        auth = AuthService()
        result = auth.login("test@example.com", "password")
        assert result is not None
        assert "token" in result

    def test_login_failure(self):
        auth = AuthService()
        result = auth.login(None, None)
        assert result is None
