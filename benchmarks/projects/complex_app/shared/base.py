from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    TypeVar,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from complex_app.auth.models import User


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


T = TypeVar("T")


@dataclass
class BaseModel:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BaseModel:
        return cls(**data)


class BaseService(ABC):
    @abstractmethod
    def _validate(self, user: Optional[User] = None) -> None:
        ...

    @abstractmethod
    def _authorize(self, user: Optional[User] = None) -> None:
        ...


class Repository(ABC, Generic[T]):
    @abstractmethod
    def create(self, entity: T) -> T:
        ...

    @abstractmethod
    def read(self, id: str) -> Optional[T]:
        ...

    @abstractmethod
    def update(self, entity: T) -> T:
        ...

    @abstractmethod
    def delete(self, id: str) -> None:
        ...

    @abstractmethod
    def list(self) -> List[T]:
        ...


class EventHandler(ABC):
    @abstractmethod
    def handle(self, event: Any) -> None:
        ...
