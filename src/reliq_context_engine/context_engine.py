from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from .memory_integration import JSONMemoryStore
from .models import BuiltContext, TaskSpec
from .prompt_builder import build_prompt
from .retriever import HybridRetriever


class ContextEngine:
    def __init__(
        self,
        wiki_dir: str | Path | None = None,
        faiss_index: str | Path | None = None,
        faiss_metadata: str | Path | None = None,
        memory_file: str | Path | None = None,
        knowledge_limit: int = 3,
        memory_limit: int = 3,
    ) -> None:
        default_root = Path.cwd() / "knowledge"
        resolved_wiki_dir = wiki_dir or os.getenv("RELIQ_KNOWLEDGE_WIKI") or (default_root / "wiki")
        resolved_faiss_index = faiss_index or os.getenv("RELIQ_FAISS_INDEX")
        resolved_faiss_metadata = faiss_metadata or os.getenv("RELIQ_FAISS_METADATA")
        resolved_memory_file = memory_file or os.getenv("RELIQ_MEMORY_FILE") or (Path.cwd() / "memory" / "memory.json")

        self.retriever = HybridRetriever(resolved_wiki_dir, resolved_faiss_index, resolved_faiss_metadata)
        self.memory = JSONMemoryStore(resolved_memory_file)
        self.knowledge_limit = knowledge_limit
        self.memory_limit = memory_limit

    def build_context(self, task: str | dict | TaskSpec) -> BuiltContext:
        task_spec = TaskSpec.from_any(task)
        knowledge = self.retriever.search(task_spec, limit=self.knowledge_limit)
        memory = self.memory.search(task_spec, limit=self.memory_limit)
        notes = []
        if not knowledge:
            notes.append("No knowledge hits found; relying on task and memory only.")
        if not memory:
            notes.append("No relevant memory hits found.")
        return BuiltContext(task=task_spec, knowledge=knowledge, memory=memory, notes=notes)

    def build_prompt(self, task: str | dict | TaskSpec) -> str:
        return build_prompt(self.build_context(task))

    def run(self, task: str | dict | TaskSpec, runner: Callable[[str], str]) -> str:
        prompt = self.build_prompt(task)
        return runner(prompt)
