"""User management service."""
from src.models.user import User, AdminUser
from src.core.redis import RedisClient
from src.core.logger import get_logger


class UserService:
    def __init__(self):
        self.redis = RedisClient()
        self.logger = get_logger(__name__)
        self._users = {}

    def create_user(self, email, role="user"):
        user_id = len(self._users) + 1
        if role == "admin":
            user = AdminUser(user_id, email)
        else:
            user = User(user_id, email)
        self._users[user_id] = user
        self.redis.set(f"user:{user_id}", user.to_dict())
        self.logger.info(f"Created user {user_id}: {email}")
        return user

    def get_profile(self, user_id):
        user = self._users.get(user_id)
        if user:
            return user.to_dict()
        return None

    def deactivate_user(self, user_id):
        user = self._users.get(user_id)
        if user:
            user.deactivate()
            self.redis.set(f"user:{user_id}", user.to_dict())
            return True
        return False
