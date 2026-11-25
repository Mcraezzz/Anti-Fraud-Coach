from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class KnowledgeItem:
    id: str
    source: str
    title: str
    text: str
    language: str = "mixed"
    category: str = ""
    risk_level: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KnowledgeItem":
        return cls(**payload)


@dataclass
class IocStore:
    domains: set[str] = field(default_factory=set)
    urls: set[str] = field(default_factory=set)

