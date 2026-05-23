"""User service server - handles user profile management operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
import asyncio
import uuid

from shared.events import EventBus, Event, EventType, get_event_bus
from shared.tracing import Tracer, trace, SpanKind
from shared.retry import retry, AsyncRetryPolicy, BackoffStrategy
from shared.circuit_breaker import CircuitBreaker, get_circuit_breaker
from shared.logging import get_logger
from shared.metrics import MetricsCollector, get_collector, counter, histogram

from services.users.handlers import UserHandler, CreateUserRequest, UpdateUserRequest, DeleteUserRequest, GetUserRequest
from services.users.handlers import CreateUserHandler, UpdateUserHandler, DeleteUserHandler, GetUserHandler, ListUsersHandler
from services.users.db import UserRepository, InMemoryUserRepository
from services.users.models import UserProfile, UserStatus


class UserCommand(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    GET = "get"
    LIST = "list"
    SEARCH = "search"


@dataclass
class UserServiceResponse:
    success: bool
    user: Optional[UserProfile] = None
    users: List[UserProfile] = field(default_factory=list)
    error: Optional[str] = None
    error_code: Optional[str] = None


class UserServiceServer:
    def __init__(
        self,
        repository: UserRepository,
        event_bus: EventBus,
        tracer: Tracer,
        handlers: Optional[Dict[UserCommand, UserHandler]] = None
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.tracer = tracer
        self.logger = get_logger("UserServiceServer", "users-service")
        self.metrics = get_collector("users-service")
        self.circuit_breaker = get_circuit_breaker("users-service", failure_threshold=5)
        self._handlers: Dict[UserCommand, UserHandler] = handlers or {}

    def register_handler(self, command: UserCommand, handler: UserHandler) -> None:
        self._handlers[command] = handler

    def _get_handler(self, command: UserCommand) -> Optional[UserHandler]:
        return self._handlers.get(command)

    @trace("user_service_create", SpanKind.SERVER)
    @histogram("user_operation_duration_seconds", service="users-service")
    async def create_user(self, request: CreateUserRequest) -> UserServiceResponse:
        self.metrics.increment_counter("user_operations_total")
        self.metrics.increment_counter("user_create_operations_total")

        handler = self._get_handler(UserCommand.CREATE)
        if not handler:
            return UserServiceResponse(
                success=False,
                error="No handler registered for CREATE command",
                error_code="INTERNAL_ERROR"
            )

        try:
            async with self.tracer.trace("validate_request", SpanKind.INTERNAL):
                if not request.email:
                    return UserServiceResponse(
                        success=False,
                        error="Email is required",
                        error_code="VALIDATION_ERROR"
                    )

            async with self.tracer.trace("execute_handler", SpanKind.INTERNAL):
                result = await self.circuit_breaker.execute(handler.handle, request)

            if result.success and result.user:
                await self.event_bus.publish(Event(
                    event_type=EventType.USER_CREATED,
                    payload={
                        "user_id": str(result.user.user_id),
                        "email": result.user.email,
                        "request_id": request.request_id
                    },
                    source="users-service"
                ))
                self.logger.info(f"Created user: {result.user.user_id}")
                self.metrics.increment_counter("user_create_successes_total")

            return UserServiceResponse(
                success=result.success,
                user=result.user,
                error=result.error,
                error_code=result.error_code
            )

        except Exception as e:
            self.logger.error(f"Failed to create user", {"error": str(e)}, exc_info=e)
            self.metrics.increment_counter("user_operations_errors_total")
            return UserServiceResponse(
                success=False,
                error=str(e),
                error_code="INTERNAL_ERROR"
            )

    @trace("user_service_update", SpanKind.SERVER)
    @histogram("user_operation_duration_seconds", service="users-service")
    async def update_user(self, request: UpdateUserRequest) -> UserServiceResponse:
        self.metrics.increment_counter("user_operations_total")
        self.metrics.increment_counter("user_update_operations_total")

        handler = self._get_handler(UserCommand.UPDATE)
        if not handler:
            return UserServiceResponse(
                success=False,
                error="No handler registered for UPDATE command",
                error_code="INTERNAL_ERROR"
            )

        try:
            result = await self.circuit_breaker.execute(handler.handle, request)

            if result.success and result.user:
                await self.event_bus.publish(Event(
                    event_type=EventType.USER_UPDATED,
                    payload={
                        "user_id": str(result.user.user_id),
                        "request_id": request.request_id,
                        "updated_fields": list(request.updates.keys()) if request.updates else []
                    },
                    source="users-service"
                ))
                self.logger.info(f"Updated user: {result.user.user_id}")
                self.metrics.increment_counter("user_update_successes_total")

            return UserServiceResponse(
                success=result.success,
                user=result.user,
                error=result.error,
                error_code=result.error_code
            )

        except Exception as e:
            self.logger.error(f"Failed to update user", {"error": str(e)}, exc_info=e)
            self.metrics.increment_counter("user_operations_errors_total")
            return UserServiceResponse(
                success=False,
                error=str(e),
                error_code="INTERNAL_ERROR"
            )

    @trace("user_service_delete", SpanKind.SERVER)
    async def delete_user(self, request: DeleteUserRequest) -> UserServiceResponse:
        self.metrics.increment_counter("user_operations_total")

        handler = self._get_handler(UserCommand.DELETE)
        if not handler:
            return UserServiceResponse(success=False, error="No handler for DELETE")

        result = await handler.handle(request)

        if result.success:
            await self.event_bus.publish(Event(
                event_type=EventType.USER_DELETED,
                payload={
                    "user_id": str(request.user_id),
                    "request_id": request.request_id
                },
                source="users-service"
            ))
            self.logger.info(f"Deleted user: {request.user_id}")

        return UserServiceResponse(
            success=result.success,
            error=result.error,
            error_code=result.error_code
        )

    @trace("user_service_get", SpanKind.SERVER)
    async def get_user(self, request: GetUserRequest) -> UserServiceResponse:
        self.metrics.increment_counter("user_operations_total")

        handler = self._get_handler(UserCommand.GET)
        if not handler:
            return UserServiceResponse(success=False, error="No handler for GET")

        result = await handler.handle(request)

        if result.user:
            self.logger.info(f"Retrieved user: {result.user.user_id}")

        return UserServiceResponse(
            success=result.success,
            user=result.user,
            error=result.error,
            error_code=result.error_code
        )


def create_user_server() -> UserServiceServer:
    event_bus = get_event_bus()
    tracer = Tracer("users-service")
    repository = InMemoryUserRepository()

    server = UserServiceServer(repository, event_bus, tracer)

    server.register_handler(UserCommand.CREATE, CreateUserHandler(repository, event_bus))
    server.register_handler(UserCommand.UPDATE, UpdateUserHandler(repository, event_bus))
    server.register_handler(UserCommand.DELETE, DeleteUserHandler(repository, event_bus))
    server.register_handler(UserCommand.GET, GetUserHandler(repository, event_bus))
    server.register_handler(UserCommand.LIST, ListUsersHandler(repository, event_bus))

    return server
