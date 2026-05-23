"""Admin service with elevated privileges."""
from src.models.user import User, AdminUser
from src.services.user import UserService
from src.core.redis import RedisClient
from src.core.logger import get_logger


class AdminService:
    def __init__(self):
        self.user_service = UserService()
        self.redis = RedisClient()
        self.logger = get_logger(__name__)

    def list_users(self):
        return []

    def promote_user(self, user_id, email):
        admin = AdminUser(user_id, email)
        self.logger.info(f"Promoted user {user_id} to admin")
        return admin

    def system_health(self):
        return {"status": "healthy", "users": 0, "services": ["auth", "redis"]}
