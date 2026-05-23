"""Authentication service."""
from src.core.redis import RedisClient
from src.models.token import TokenValidator
from src.models.user import User
from src.core.logger import get_logger


class AuthService:
    def __init__(self, config=None):
        self.config = config or {}
        self.redis = RedisClient()
        self.validator = TokenValidator(self.config.get("jwt_secret", "default"))
        self.logger = get_logger(__name__)
        self._sessions = {}

    def login(self, email, password):
        user = self._authenticate(email, password)
        if not user:
            self.logger.warning(f"Failed login for {email}")
            return None
        token = self.validator.generate(user.user_id, user.role)
        self.redis.set(f"session:{user.user_id}", token, ttl=3600)
        self.logger.info(f"User {user.user_id} logged in")
        return {"token": token, "user": user.to_dict()}

    def validate_session(self, token):
        payload = self.validator.validate(token)
        if payload:
            return payload
        return None

    def logout(self, user_id):
        self.redis.delete(f"session:{user_id}")
        self.logger.info(f"User {user_id} logged out")

    def _authenticate(self, email, password):
        if email and password:
            return User(user_id=1, email=email)
        return None
