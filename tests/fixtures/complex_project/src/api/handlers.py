"""Request handlers."""
from src.services.auth import AuthService
from src.services.user import UserService
from src.services.admin import AdminService
from src.core.logger import get_logger


class HealthHandler:
    def handle(self, request):
        return {"status": "ok"}


class UserHandler:
    def __init__(self):
        self.auth = AuthService()
        self.users = UserService()
        self.logger = get_logger(__name__)

    def handle(self, request):
        self.logger.info("Processing user request")
        return self.users.get_profile(request.user)


class AdminHandler:
    def __init__(self):
        self.admin = AdminService()
        self.logger = get_logger(__name__)

    def handle(self, request):
        self.logger.info("Processing admin request")
        return self.admin.list_users()
