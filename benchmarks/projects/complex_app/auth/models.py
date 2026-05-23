from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from complex_app.shared.base import BaseModel


class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    VERIFY = "verify"


class Permission:
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class User(BaseModel):
    username: str = ""
    email: str = ""
    password_hash: str = ""
    roles: List[str] = field(default_factory=list)
    is_active: bool = True
    is_verified: bool = False
    last_login: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Role:
    name: str = ""
    permissions: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class Session(BaseModel):
    user_id: str = ""
    token: str = ""
    expires_at: Optional[str] = None
    ip_address: str = ""
    user_agent: str = ""


@dataclass
class TokenPayload:
    sub: str = ""
    type: str = ""
    exp: Optional[float] = None
    iat: Optional[float] = None
    roles: List[str] = field(default_factory=list)
