"""Users service module for user profile management."""

from services.users.server import UserServiceServer, create_user_server
from services.users.handlers import UserHandler, CreateUserHandler, UpdateUserHandler, DeleteUserHandler, GetUserHandler
from services.users.db import UserRepository, InMemoryUserRepository, DatabaseUserRepository
from services.users.models import UserProfile, UserPreferences, UserNotificationSettings, ContactInfo

__all__ = [
    "UserServiceServer", "create_user_server",
    "UserHandler", "CreateUserHandler", "UpdateUserHandler", "DeleteUserHandler", "GetUserHandler",
    "UserRepository", "InMemoryUserRepository", "DatabaseUserRepository",
    "UserProfile", "UserPreferences", "UserNotificationSettings", "ContactInfo"
]
