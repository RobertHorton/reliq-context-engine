from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

MEMORY_SCOPES = ("user", "system", "session")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskSpec:
    task: str
    type: str = "general"
    target: str | None = None
    user_id: str | None = None
    session_id: str | None = None
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
            user_id=value.get("user_id"),
            session_id=value.get("session_id"),
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
    scope: str = "user"
    key: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    access_count: int = 0
    importance: float = 0.5

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MemoryItem":
        created_at = value.get("created_at") or utc_now()
        updated_at = value.get("updated_at") or created_at
        return cls(
            content=value["content"],
            kind=value.get("kind", "semantic"),
            tags=list(value.get("tags", [])),
            metadata=dict(value.get("metadata", {})),
            scope=value.get("scope", "user"),
            key=value.get("key"),
            user_id=value.get("user_id"),
            session_id=value.get("session_id"),
            created_at=created_at,
            updated_at=updated_at,
            access_count=int(value.get("access_count", 0)),
            importance=float(value.get("importance", 0.5)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryHit:
    content: str
    kind: str
    tags: list[str]
    score: float
    scope: str = "user"
    key: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    access_count: int = 0
    importance: float = 0.5

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


@dataclass
class ExtractedMemory:
    content: str
    scope: str
    kind: str = "semantic"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    key: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    importance: float = 0.5

    def to_item(self) -> MemoryItem:
        return MemoryItem(
            content=self.content,
            kind=self.kind,
            tags=list(self.tags),
            metadata=dict(self.metadata),
            scope=self.scope,
            key=self.key,
            user_id=self.user_id,
            session_id=self.session_id,
            importance=self.importance,
        )


@dataclass
class CognitionResult:
    task: TaskSpec
    context: BuiltContext
    prompt: str
    response: str | None = None
    memory_updates: list[MemoryItem] = field(default_factory=list)
    evolution_logged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task.to_dict(),
            "context": self.context.to_dict(),
            "prompt": self.prompt,
            "response": self.response,
            "memory_updates": [item.to_dict() for item in self.memory_updates],
            "evolution_logged": self.evolution_logged,
        }


@dataclass
class AgentProfile:
    name: str
    vram_gb: float
    priority: int
    concurrency: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimeStatus:
    mode: str
    gpu_available: bool
    gpu_name: str | None = None
    gpu_utilization_pct: float | None = None
    vram_total_gb: float | None = None
    vram_used_gb: float | None = None
    vram_free_gb: float | None = None
    notes: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SchedulerDecision:
    allowed: bool
    mode: str
    agent_type: str
    required_vram_gb: float
    available_vram_gb: float | None
    reason: str
    profile: AgentProfile
    generated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["profile"] = self.profile.to_dict()
        return payload


@dataclass
class DashboardTask:
    task_id: str
    goal: str
    agent_type: str
    status: str
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    detail: str | None = None
    evaluation_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SwarmRunResult:
    goal: str
    agent_type: str
    decision: SchedulerDecision
    cognition: CognitionResult | None = None
    evaluation_score: float | None = None
    task_id: str | None = None
    generated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "agent_type": self.agent_type,
            "decision": self.decision.to_dict(),
            "cognition": self.cognition.to_dict() if self.cognition is not None else None,
            "evaluation_score": self.evaluation_score,
            "task_id": self.task_id,
            "generated_at": self.generated_at,
        }
