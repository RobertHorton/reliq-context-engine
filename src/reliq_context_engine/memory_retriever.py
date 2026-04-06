from __future__ import annotations

from pathlib import Path

from .memory_store import MultiMemoryStore
from .models import MemoryHit, TaskSpec


class MemoryRetriever:
    def __init__(
        self,
        memory_dir: str | Path,
        user_path: str | Path | None = None,
        system_path: str | Path | None = None,
        session_path: str | Path | None = None,
    ) -> None:
        self.store = MultiMemoryStore(
            memory_dir=memory_dir,
            user_path=user_path,
            system_path=system_path,
            session_path=session_path,
        )

    @property
    def path(self) -> Path:
        return self.store.path

    @property
    def paths(self) -> dict[str, Path]:
        return self.store.paths

    def search(self, task: TaskSpec | str, limit: int = 3) -> list[MemoryHit]:
        task_spec = TaskSpec.from_any(task)
        return self.store.search(task_spec, limit=limit)

    def snapshot(self, scope: str | None = None, user_id: str | None = None, session_id: str | None = None) -> dict[str, list[dict]]:
        return self.store.snapshot(scope=scope, user_id=user_id, session_id=session_id)

    def clear(self, scope: str | None = None, user_id: str | None = None, session_id: str | None = None) -> None:
        self.store.clear(scope=scope, user_id=user_id, session_id=session_id)

    def prune(self, limit_per_scope: int = 100) -> dict[str, int]:
        return self.store.prune(limit_per_scope=limit_per_scope)
