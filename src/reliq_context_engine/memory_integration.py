from __future__ import annotations

import json
import re
from pathlib import Path

from .models import MemoryHit, MemoryItem, TaskSpec

STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9_\\-]{3,}", text.lower())
        if token not in STOPWORDS
    }


class JSONMemoryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def load(self) -> list[MemoryItem]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [
            MemoryItem(
                content=item["content"],
                kind=item.get("kind", "semantic"),
                tags=list(item.get("tags", [])),
                metadata=dict(item.get("metadata", {})),
                created_at=item.get("created_at"),
            )
            for item in raw
        ]

    def save(self, items: list[MemoryItem]) -> None:
        payload = [item.to_dict() for item in items]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add(self, item: MemoryItem | dict) -> MemoryItem:
        memory_item = item if isinstance(item, MemoryItem) else MemoryItem(**item)
        items = self.load()
        items.append(memory_item)
        self.save(items)
        return memory_item

    def search(self, task: TaskSpec | str, limit: int = 3) -> list[MemoryHit]:
        task_spec = TaskSpec.from_any(task)
        query_tokens = tokenize(" ".join([task_spec.task, task_spec.type, task_spec.target or ""]))
        hits: list[MemoryHit] = []
        for item in self.load():
            haystack = " ".join([item.content, item.kind, " ".join(item.tags)])
            overlap = query_tokens.intersection(tokenize(haystack))
            if not overlap:
                continue
            score = len(overlap) / max(len(query_tokens), 1)
            if task_spec.type and task_spec.type in haystack.lower():
                score += 0.15
            hits.append(
                MemoryHit(
                    content=item.content,
                    kind=item.kind,
                    tags=item.tags,
                    score=round(score, 4),
                    metadata=item.metadata,
                    created_at=item.created_at,
                )
            )
        return sorted(hits, key=lambda item: item.score, reverse=True)[:limit]
