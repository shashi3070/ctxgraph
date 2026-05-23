"""Data models for auth service: User, Token, Session, etc."""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"
    PENDING_VERIFICATION = "pending_verification"


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"
    SERVICE_ACCOUNT = "service_account"


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    VIEW_AUDIT = "view_audit"
    EXPORT_DATA = "export_data"
    IMPORT_DATA = "import_data"
    API_ACCESS = "api_access"


class TokenStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    USED = "used"


class TokenPurpose(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    VERIFY_EMAIL = "verify_email"
    INVITE = "invite"
    MAGIC_LINK = "magic_link"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    LOGGED_OUT = "logged_out"
    REVOKED = "revoked"


class AuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    APPLE = "apple"
    LINKEDIN = "linkedin"
    SAML = "saml"
    LDAP = "ldap"


@dataclass
class User:
    user_id: uuid.UUID
    email: str
    roles: List[UserRole]
    permissions: List[Permission]
    username: Optional[str] = None
    password_hash: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    auth_provider: AuthProvider = AuthProvider.LOCAL
    auth_provider_id: Optional[str] = None
    email_verified: bool = False
    phone_verified: bool = False
    mfa_enabled: bool = False
    mfa_methods: List[str] = field(default_factory=list)
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_role(self, role: UserRole) -> bool:
        return role in self.roles or UserRole.SUPER_ADMIN in self.roles

    def has_permission(self, permission: Permission) -> bool:
        if UserRole.SUPER_ADMIN in self.roles:
            return True
        if permission in self.permissions:
            return True
        role_permission_map = {
            UserRole.ADMIN: {Permission.READ, Permission.WRITE, Permission.DELETE},
            UserRole.MODERATOR: {Permission.READ, Permission.WRITE},
            UserRole.USER: {Permission.READ},
        }
        for role in self.roles:
            if permission in role_permission_map.get(role, set()):
                return True
        return False

    def is_locked(self) -> bool:
        if self.status == UserStatus.SUSPENDED or self.status == UserStatus.BANNED:
            return True
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        return False

    def full_name(self) -> Optional[str]:
        if self.display_name:
            return self.display_name
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.username


@dataclass
class Token:
    token_id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    purpose: TokenPurpose
    status: TokenStatus = TokenStatus.ACTIVE
    scope: Optional[str] = None
    client_id: Optional[str] = None
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_by_ip: Optional[str] = None
    created_by_user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        if self.status != TokenStatus.ACTIVE:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def revoke(self) -> None:
        self.status = TokenStatus.REVOKED
        self.revoked_at = datetime.utcnow()

    def use(self) -> None:
        if self.purpose in [TokenPurpose.RESET_PASSWORD, TokenPurpose.VERIFY_EMAIL, TokenPurpose.INVITE]:
            self.status = TokenStatus.USED
            self.used_at = datetime.utcnow()

    def expires_in_seconds(self) -> Optional[int]:
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))


@dataclass
class Session:
    session_id: uuid.UUID
    user_id: uuid.UUID
    status: SessionStatus = SessionStatus.ACTIVE
    token_id: Optional[uuid.UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Dict[str, Any] = field(default_factory=dict)
    location_info: Dict[str, Any] = field(default_factory=dict)
    auth_method: Optional[str] = None
    auth_provider: Optional[AuthProvider] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    logged_out_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    impersonated_by_user_id: Optional[uuid.UUID] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        if self.status != SessionStatus.ACTIVE:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def record_activity(self) -> None:
        self.last_activity_at = datetime.utcnow()

    def logout(self) -> None:
        self.status = SessionStatus.LOGGED_OUT
        self.logged_out_at = datetime.utcnow()

    def revoke(self) -> None:
        self.status = SessionStatus.REVOKED
        self.revoked_at = datetime.utcnow()

    def duration_seconds(self) -> Optional[int]:
        if not self.created_at:
            return None
        end_time = self.logged_out_at or self.revoked_at or datetime.utcnow()
        return int((end_time - self.created_at).total_seconds())

    def idle_seconds(self) -> int:
        return int((datetime.utcnow() - self.last_activity_at).total_seconds())


@dataclass
class RefreshToken:
    token_id: str
    user_id: str
    client_id: str
    token_hash: str
    scope: str
    issued_at: datetime
    expires_at: datetime
    used: bool = False
    invalidated: bool = False
    replaced_by_token_id: Optional[str] = None
    created_by_ip: Optional[str] = None
    created_by_user_agent: Optional[str] = None


@dataclass
class UserInvite:
    invite_id: uuid.UUID
    email: str
    inviter_user_id: uuid.UUID
    token_hash: str
    status: str = "pending"
    roles: List[UserRole] = field(default_factory=lambda: [UserRole.USER])
    message: Optional[str] = None
    sent_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    accepted_by_user_id: Optional[uuid.UUID] = None
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_valid(self) -> bool:
        if self.status != "pending":
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True


@dataclass
class AuditEntry:
    entry_id: uuid.UUID
    timestamp: datetime
    user_id: Optional[uuid.UUID]
    action: str
    resource_type: str
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    status: str
    details: Dict[str, Any]
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
