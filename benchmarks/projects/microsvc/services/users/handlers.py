"""CRUD handlers for user operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Generic
import asyncio
import uuid

from shared.events import EventBus, Event, EventType
from shared.tracing import Tracer, trace, SpanKind
from shared.retry import retry
from shared.logging import get_logger
from shared.metrics import get_collector

from services.users.db import UserRepository
from services.users.models import UserProfile, UserStatus, UserPreferences, ContactInfo


TRequest = TypeVar('TRequest')
TResponse = TypeVar('TResponse')


@dataclass
class HandlerResult:
    success: bool
    user: Optional[UserProfile] = None
    users: List[UserProfile] = field(default_factory=list)
    error: Optional[str] = None
    error_code: Optional[str] = None


class UserHandler(ABC, Generic[TRequest, TResponse]):
    def __init__(self, repository: UserRepository, event_bus: EventBus):
        self.repository = repository
        self.event_bus = event_bus
        self.logger = get_logger(self.__class__.__name__, "users-service")
        self.metrics = get_collector("users-service")

    @abstractmethod
    async def handle(self, request: TRequest) -> HandlerResult:
        pass

    @abstractmethod
    def validate(self, request: TRequest) -> Optional[HandlerResult]:
        pass


@dataclass
class CreateUserRequest:
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password_hash: Optional[str] = None
    auth_provider: str = "local"
    auth_provider_id: Optional[str] = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateUserRequest:
    user_id: uuid.UUID
    updates: Dict[str, Any]
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeleteUserRequest:
    user_id: uuid.UUID
    soft_delete: bool = True
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class GetUserRequest:
    user_id: Optional[uuid.UUID] = None
    email: Optional[str] = None
    username: Optional[str] = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ListUsersRequest:
    page: int = 1
    page_size: int = 20
    status: Optional[UserStatus] = None
    search_query: Optional[str] = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class CreateUserHandler(UserHandler[CreateUserRequest, HandlerResult]):
    @trace("create_user_handler", SpanKind.INTERNAL)
    @retry(max_attempts=3, initial_delay_ms=100)
    async def handle(self, request: CreateUserRequest) -> HandlerResult:
        validation_error = self.validate(request)
        if validation_error:
            return validation_error

        existing = await self.repository.find_by_email(request.email)
        if existing:
            return HandlerResult(
                success=False,
                error=f"User with email {request.email} already exists",
                error_code="DUPLICATE_EMAIL"
            )

        if request.username:
            existing_by_username = await self.repository.find_by_username(request.username)
            if existing_by_username:
                return HandlerResult(
                    success=False,
                    error=f"Username {request.username} is already taken",
                    error_code="DUPLICATE_USERNAME"
                )

        user_profile = UserProfile(
            user_id=uuid.uuid4(),
            email=request.email,
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name,
            password_hash=request.password_hash,
            status=UserStatus.PENDING_VERIFICATION,
            auth_provider=request.auth_provider,
            auth_provider_id=request.auth_provider_id,
            preferences=UserPreferences(),
            contact_info=ContactInfo(email=request.email),
            metadata=request.metadata
        )

        created = await self.repository.create(user_profile)

        self.logger.info(f"Created user profile: {created.user_id}")
        self.metrics.increment_counter("users_created_total")

        return HandlerResult(success=True, user=created)

    def validate(self, request: CreateUserRequest) -> Optional[HandlerResult]:
        if not request.email:
            return HandlerResult(
                success=False,
                error="Email is required",
                error_code="VALIDATION_ERROR"
            )
        if "@" not in request.email:
            return HandlerResult(
                success=False,
                error="Invalid email format",
                error_code="VALIDATION_ERROR"
            )
        return None


class UpdateUserHandler(UserHandler[UpdateUserRequest, HandlerResult]):
    @trace("update_user_handler", SpanKind.INTERNAL)
    async def handle(self, request: UpdateUserRequest) -> HandlerResult:
        validation_error = self.validate(request)
        if validation_error:
            return validation_error

        existing = await self.repository.find_by_id(request.user_id)
        if not existing:
            return HandlerResult(
                success=False,
                error=f"User {request.user_id} not found",
                error_code="NOT_FOUND"
            )

        allowed_fields = {
            "username", "first_name", "last_name", "display_name", "avatar_url",
            "phone_number", "timezone", "locale", "status", "metadata"
        }

        updates = {k: v for k, v in request.updates.items() if k in allowed_fields}

        if not updates:
            return HandlerResult(success=True, user=existing)

        if "email" in request.updates:
            return HandlerResult(
                success=False,
                error="Email cannot be updated directly",
                error_code="VALIDATION_ERROR"
            )

        updated = await self.repository.update(request.user_id, updates)

        if updated:
            self.logger.info(f"Updated user profile: {request.user_id}")
            self.metrics.increment_counter("users_updated_total")

        return HandlerResult(success=True, user=updated)

    def validate(self, request: UpdateUserRequest) -> Optional[HandlerResult]:
        if not request.user_id:
            return HandlerResult(
                success=False,
                error="User ID is required",
                error_code="VALIDATION_ERROR"
            )
        return None


class DeleteUserHandler(UserHandler[DeleteUserRequest, HandlerResult]):
    @trace("delete_user_handler", SpanKind.INTERNAL)
    async def handle(self, request: DeleteUserRequest) -> HandlerResult:
        validation_error = self.validate(request)
        if validation_error:
            return validation_error

        existing = await self.repository.find_by_id(request.user_id)
        if not existing:
            return HandlerResult(
                success=False,
                error=f"User {request.user_id} not found",
                error_code="NOT_FOUND"
            )

        if request.soft_delete:
            updates = {
                "status": UserStatus.INACTIVE.value if isinstance(UserStatus.INACTIVE.value, str) else UserStatus.INACTIVE,
                "deleted_at": datetime.utcnow()
            }
            await self.repository.update(request.user_id, updates)
            self.logger.info(f"Soft deleted user: {request.user_id}")
        else:
            await self.repository.delete(request.user_id)
            self.logger.info(f"Hard deleted user: {request.user_id}")

        self.metrics.increment_counter("users_deleted_total")

        return HandlerResult(success=True)

    def validate(self, request: DeleteUserRequest) -> Optional[HandlerResult]:
        if not request.user_id:
            return HandlerResult(
                success=False,
                error="User ID is required",
                error_code="VALIDATION_ERROR"
            )
        return None


class GetUserHandler(UserHandler[GetUserRequest, HandlerResult]):
    @trace("get_user_handler", SpanKind.INTERNAL)
    async def handle(self, request: GetUserRequest) -> HandlerResult:
        validation_error = self.validate(request)
        if validation_error:
            return validation_error

        user: Optional[UserProfile] = None

        if request.user_id:
            user = await self.repository.find_by_id(request.user_id)
        elif request.email:
            user = await self.repository.find_by_email(request.email)
        elif request.username:
            user = await self.repository.find_by_username(request.username)

        if user:
            self.metrics.increment_counter("users_retrieved_total")
            return HandlerResult(success=True, user=user)

        return HandlerResult(
            success=False,
            error="User not found",
            error_code="NOT_FOUND"
        )

    def validate(self, request: GetUserRequest) -> Optional[HandlerResult]:
        if not request.user_id and not request.email and not request.username:
            return HandlerResult(
                success=False,
                error="At least one of user_id, email, or username is required",
                error_code="VALIDATION_ERROR"
            )
        return None


class ListUsersHandler(UserHandler[ListUsersRequest, HandlerResult]):
    @trace("list_users_handler", SpanKind.INTERNAL)
    async def handle(self, request: ListUsersRequest) -> HandlerResult:
        users = await self.repository.find_all(
            page=request.page,
            page_size=request.page_size,
            status=request.status
        )

        self.metrics.increment_counter("users_listed_total")

        return HandlerResult(success=True, users=users)

    def validate(self, request: ListUsersRequest) -> Optional[HandlerResult]:
        if request.page < 1:
            return HandlerResult(
                success=False,
                error="Page must be >= 1",
                error_code="VALIDATION_ERROR"
            )
        if request.page_size < 1 or request.page_size > 100:
            return HandlerResult(
                success=False,
                error="Page size must be between 1 and 100",
                error_code="VALIDATION_ERROR"
            )
        return None
