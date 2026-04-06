from __future__ import annotations

from pathlib import Path

from .memory_extractor import extract_memory
from .memory_retriever import MemoryRetriever
from .models import MemoryItem, TaskSpec


class MemoryManager:
    def __init__(
        self,
        memory_dir: str | Path,
        user_path: str | Path | None = None,
        system_path: str | Path | None = None,
        session_path: str | Path | None = None,
    ) -> None:
        self.retriever = MemoryRetriever(
            memory_dir=memory_dir,
            user_path=user_path,
            system_path=system_path,
            session_path=session_path,
        )
        self.path = self.retriever.path
        self.paths = self.retriever.paths

    def add(self, item: MemoryItem | dict) -> MemoryItem:
        memory_item = item if isinstance(item, MemoryItem) else MemoryItem.from_dict(item)
        return self.retriever.store.add(memory_item)

    def search(self, task: TaskSpec | str, limit: int = 3):
        return self.retriever.search(task, limit=limit)

    def process_interaction(self, user_input: str, response: str | None = None, task: TaskSpec | str | None = None) -> list[MemoryItem]:
        task_spec = TaskSpec.from_any(task or user_input)
        extracted = extract_memory(user_input, response, task_spec)
        return [self.add(item.to_item()) for item in extracted]

    def get_memory(self, scope: str | None = None, user_id: str | None = None, session_id: str | None = None) -> dict[str, list[dict]]:
        return self.retriever.snapshot(scope=scope, user_id=user_id, session_id=session_id)

    def clear_memory(self, scope: str | None = None, user_id: str | None = None, session_id: str | None = None) -> None:
        self.retriever.clear(scope=scope, user_id=user_id, session_id=session_id)

    def prune_memory(self, limit_per_scope: int = 100) -> dict[str, int]:
        return self.retriever.prune(limit_per_scope=limit_per_scope)
