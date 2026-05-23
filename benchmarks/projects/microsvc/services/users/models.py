"""User profile models for user service."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"
    SUSPENDED = "suspended"
    BANNED = "banned"


class Timezone(str, Enum):
    UTC = "UTC"
    US_EASTERN = "America/New_York"
    US_CENTRAL = "America/Chicago"
    US_PACIFIC = "America/Los_Angeles"
    EU_LONDON = "Europe/London"
    EU_PARIS = "Europe/Paris"
    ASIA_TOKYO = "Asia/Tokyo"
    ASIA_SINGAPORE = "Asia/Singapore"
    AU_SYDNEY = "Australia/Sydney"


class Locale(str, Enum):
    EN_US = "en_US"
    EN_GB = "en_GB"
    ES_ES = "es_ES"
    FR_FR = "fr_FR"
    DE_DE = "de_DE"
    JA_JP = "ja_JP"
    ZH_CN = "zh_CN"
    PT_BR = "pt_BR"


@dataclass
class ContactInfo:
    email: str
    phone_number: Optional[str] = None
    alternate_email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


@dataclass
class UserNotificationSettings:
    email_enabled: bool = True
    push_enabled: bool = True
    sms_enabled: bool = False
    marketing_enabled: bool = False
    product_updates_enabled: bool = True
    security_alerts_enabled: bool = True
    billing_alerts_enabled: bool = True


@dataclass
class UserPreferences:
    timezone: Timezone = Timezone.UTC
    locale: Locale = Locale.EN_US
    theme: str = "light"
    notifications: UserNotificationSettings = field(default_factory=UserNotificationSettings)
    date_format: str = "MM/DD/YYYY"
    time_format: str = "12h"
    language: str = "en"


@dataclass
class UserSocialLinks:
    github: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None


@dataclass
class UserProfile:
    user_id: uuid.UUID
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    password_hash: Optional[str] = None
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    auth_provider: str = "local"
    auth_provider_id: Optional[str] = None
    email_verified: bool = False
    phone_verified: bool = False
    mfa_enabled: bool = False
    mfa_methods: List[str] = field(default_factory=list)
    timezone: Timezone = Timezone.UTC
    locale: Locale = Locale.EN_US
    preferences: UserPreferences = field(default_factory=UserPreferences)
    contact_info: ContactInfo = field(default_factory=lambda: ContactInfo(email=""))
    social_links: UserSocialLinks = field(default_factory=UserSocialLinks)
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    last_active_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def full_name(self) -> Optional[str]:
        if self.display_name:
            return self.display_name
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.username

    def initials(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        if self.display_name:
            parts = self.display_name.split()
            if len(parts) >= 2:
                return f"{parts[0][0]}{parts[-1][0]}".upper()
            return parts[0][:2].upper() if parts else "?"
        if self.email:
            return self.email[0].upper()
        return "?"

    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    def is_verified(self) -> bool:
        return self.email_verified

    def is_locked(self) -> bool:
        if self.status in (UserStatus.SUSPENDED, UserStatus.BANNED):
            return True
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        return False

    def record_login(self, ip_address: Optional[str] = None) -> None:
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address
        self.failed_login_attempts = 0
        self.locked_until = None

    def record_failed_login(self, max_attempts: int = 5, lockout_minutes: int = 15) -> None:
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)


@dataclass
class UserSearchResult:
    user_id: uuid.UUID
    email: str
    username: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    status: UserStatus
    created_at: datetime
    score: Optional[float] = None


@dataclass
class UserActivity:
    activity_id: uuid.UUID
    user_id: uuid.UUID
    activity_type: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Dict[str, Any]
    occurred_at: datetime
