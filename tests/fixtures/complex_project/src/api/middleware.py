"""HTTP middleware components."""
from src.core.redis import RedisClient
from src.models.token import TokenValidator


class AuthMiddleware:
    def __init__(self, jwt_secret):
        self.redis = RedisClient()
        self.validator = TokenValidator(jwt_secret)

    def authenticate(self, request):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return False
        payload = self.validator.validate(token)
        if payload:
            request.user = payload.get("sub")
            return True
        return False


class RateLimiter:
    def __init__(self, max_requests=100):
        self.max_requests = max_requests

    def check(self, request):
        return True
