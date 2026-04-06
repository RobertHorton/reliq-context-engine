from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskSpec:
    task: str
    type: str = "general"
    target: str | None = None
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_any(cls, value: str | dict[str, Any] | "TaskSpec") -> "TaskSpec":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(task=value)
        return cls(
            task=value["task"],
            type=value.get("type", "general"),
            target=value.get("target"),
            constraints=list(value.get("constraints", [])),
            metadata=dict(value.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeHit:
    title: str
    content: str
    source: str
    score: float
    kind: str = "wiki"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryItem:
    content: str
    kind: str = "semantic"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryHit:
    content: str
    kind: str
    tags: list[str]
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BuiltContext:
    task: TaskSpec
    knowledge: list[KnowledgeHit]
    memory: list[MemoryHit]
    generated_at: str = field(default_factory=utc_now)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task.to_dict(),
            "knowledge": [item.to_dict() for item in self.knowledge],
            "memory": [item.to_dict() for item in self.memory],
            "generated_at": self.generated_at,
            "notes": list(self.notes),
        }
