from __future__ import annotations

import json
import re
from pathlib import Path

from .models import MEMORY_SCOPES, MemoryHit, MemoryItem, TaskSpec, utc_now

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

SCOPE_PRIORITY = {
    "session": 0.3,
    "user": 0.2,
    "system": 0.1,
}


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9_\-]{3,}", text.lower())
        if token not in STOPWORDS
    }


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "default"


class JSONMemoryStore:
    def __init__(self, path: str | Path, scope: str = "user") -> None:
        if scope not in MEMORY_SCOPES:
            raise ValueError(f"Unsupported memory scope: {scope}")
        self.path = Path(path)
        self.scope = scope
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def load(self) -> list[MemoryItem]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [MemoryItem.from_dict(item) for item in raw]

    def save(self, items: list[MemoryItem]) -> None:
        payload = [item.to_dict() for item in items]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add(self, item: MemoryItem | dict) -> MemoryItem:
        memory_item = item if isinstance(item, MemoryItem) else MemoryItem.from_dict(item)
        memory_item.scope = self.scope
        items = self.load()
        updated = False
        for idx, existing in enumerate(items):
            if self._same_identity(existing, memory_item):
                items[idx] = self._merge(existing, memory_item)
                memory_item = items[idx]
                updated = True
                break
        if not updated:
            items.append(memory_item)
        self.save(items)
        return memory_item

    def clear(self) -> None:
        self.save([])

    def prune(self, limit: int = 100) -> int:
        items = self.load()
        if len(items) <= limit:
            return 0
        ranked = sorted(
            items,
            key=lambda item: (item.importance, item.access_count, item.updated_at),
            reverse=True,
        )
        kept = ranked[:limit]
        removed = len(items) - len(kept)
        self.save(kept)
        return removed

    def search(self, task: TaskSpec | str, limit: int = 3) -> list[MemoryHit]:
        task_spec = TaskSpec.from_any(task)
        query_parts = [
            task_spec.task,
            task_spec.type,
            task_spec.target or "",
            " ".join(task_spec.constraints),
        ]
        query_tokens = tokenize(" ".join(part for part in query_parts if part))
        if not query_tokens:
            return []

        items = self.load()
        scored: list[tuple[int, MemoryHit]] = []
        changed = False
        for idx, item in enumerate(items):
            haystack = " ".join(
                [
                    item.content,
                    item.kind,
                    item.key or "",
                    " ".join(item.tags),
                    json.dumps(item.metadata, sort_keys=True),
                ]
            )
            overlap = query_tokens.intersection(tokenize(haystack))
            if not overlap:
                continue
            score = len(overlap) / max(len(query_tokens), 1)
            if task_spec.type and task_spec.type in haystack.lower():
                score += 0.15
            if task_spec.target and task_spec.target.lower() in haystack.lower():
                score += 0.2
            if item.importance:
                score += min(item.importance, 1.0) * 0.1
            score += SCOPE_PRIORITY.get(self.scope, 0.0)
            if task_spec.user_id and item.user_id and task_spec.user_id == item.user_id:
                score += 0.2
            if task_spec.session_id and item.session_id and task_spec.session_id == item.session_id:
                score += 0.3

            items[idx].access_count += 1
            changed = True
            scored.append(
                (
                    idx,
                    MemoryHit(
                        content=item.content,
                        kind=item.kind,
                        tags=item.tags,
                        score=round(score, 4),
                        scope=item.scope,
                        key=item.key,
                        user_id=item.user_id,
                        session_id=item.session_id,
                        metadata=item.metadata,
                        created_at=item.created_at,
                        updated_at=item.updated_at,
                        access_count=items[idx].access_count,
                        importance=item.importance,
                    ),
                )
            )

        ranked = sorted((hit for _, hit in scored), key=lambda item: item.score, reverse=True)[:limit]
        if changed:
            self.save(items)
        return ranked

    def _same_identity(self, existing: MemoryItem, incoming: MemoryItem) -> bool:
        if existing.key and incoming.key:
            return existing.key == incoming.key
        return existing.content == incoming.content and existing.kind == incoming.kind

    def _merge(self, existing: MemoryItem, incoming: MemoryItem) -> MemoryItem:
        merged_tags = sorted({*existing.tags, *incoming.tags})
        merged_metadata = {**existing.metadata, **incoming.metadata}
        return MemoryItem(
            content=incoming.content or existing.content,
            kind=incoming.kind or existing.kind,
            tags=merged_tags,
            metadata=merged_metadata,
            scope=self.scope,
            key=incoming.key or existing.key,
            user_id=incoming.user_id or existing.user_id,
            session_id=incoming.session_id or existing.session_id,
            created_at=existing.created_at,
            updated_at=utc_now(),
            access_count=max(existing.access_count, incoming.access_count),
            importance=max(existing.importance, incoming.importance),
        )


class MultiMemoryStore:
    def __init__(
        self,
        memory_dir: str | Path,
        user_path: str | Path | None = None,
        system_path: str | Path | None = None,
        session_path: str | Path | None = None,
    ) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.users_dir = self.memory_dir / "users"
        self.sessions_dir = self.memory_dir / "sessions"
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        self.system_store = JSONMemoryStore(system_path or (self.memory_dir / "system.json"), scope="system")
        self.default_user_store = JSONMemoryStore(user_path or (self.memory_dir / "user.json"), scope="user")
        self.default_session_store = JSONMemoryStore(session_path or (self.memory_dir / "session.json"), scope="session")

        self.path = self.default_user_store.path
        self.paths = {
            "system": self.system_store.path,
            "user": self.default_user_store.path,
            "session": self.default_session_store.path,
        }

    def add(self, item: MemoryItem) -> MemoryItem:
        return self._store_for(item.scope, item.user_id, item.session_id).add(item)

    def search(self, task: TaskSpec | str, limit: int = 3) -> list[MemoryHit]:
        task_spec = TaskSpec.from_any(task)
        stores = self._stores_for_search(task_spec)
        hits: dict[str, MemoryHit] = {}
        for store in stores:
            for hit in store.search(task_spec, limit=max(limit, 5)):
                key = f"{hit.scope}:{hit.user_id or '-'}:{hit.session_id or '-'}:{hit.key or hit.content}"
                current = hits.get(key)
                if current is None or hit.score > current.score:
                    hits[key] = hit
        ranked = sorted(hits.values(), key=lambda item: item.score, reverse=True)
        return ranked[:limit]

    def snapshot(self, scope: str | None = None, user_id: str | None = None, session_id: str | None = None) -> dict[str, list[dict]]:
        selected = self._stores_for_snapshot(scope, user_id, session_id)
        return {name: [item.to_dict() for item in store.load()] for name, store in selected.items()}

    def clear(self, scope: str | None = None, user_id: str | None = None, session_id: str | None = None) -> None:
        for store in self._stores_for_snapshot(scope, user_id, session_id).values():
            store.clear()

    def prune(self, limit_per_scope: int = 100) -> dict[str, int]:
        selected = self._stores_for_snapshot(None, None, None)
        return {name: store.prune(limit_per_scope) for name, store in selected.items()}

    def _stores_for_search(self, task: TaskSpec) -> list[JSONMemoryStore]:
        stores = [self.default_session_store]
        if task.session_id:
            stores.insert(0, self._session_store(task.session_id))
        stores.append(self.default_user_store)
        if task.user_id:
            stores.insert(2, self._user_store(task.user_id))
        stores.append(self.system_store)
        return stores

    def _stores_for_snapshot(self, scope: str | None, user_id: str | None, session_id: str | None) -> dict[str, JSONMemoryStore]:
        if scope == "system":
            return {"system": self.system_store}
        if scope == "user":
            if user_id:
                return {f"user:{user_id}": self._user_store(user_id)}
            return {"user": self.default_user_store}
        if scope == "session":
            if session_id:
                return {f"session:{session_id}": self._session_store(session_id)}
            return {"session": self.default_session_store}
        selected = {
            "system": self.system_store,
            "user": self.default_user_store,
            "session": self.default_session_store,
        }
        if user_id:
            selected[f"user:{user_id}"] = self._user_store(user_id)
        if session_id:
            selected[f"session:{session_id}"] = self._session_store(session_id)
        return selected

    def _store_for(self, scope: str, user_id: str | None, session_id: str | None) -> JSONMemoryStore:
        if scope == "system":
            return self.system_store
        if scope == "session":
            return self._session_store(session_id) if session_id else self.default_session_store
        return self._user_store(user_id) if user_id else self.default_user_store

    def _user_store(self, user_id: str) -> JSONMemoryStore:
        return JSONMemoryStore(self.users_dir / f"{slugify(user_id)}.json", scope="user")

    def _session_store(self, session_id: str) -> JSONMemoryStore:
        return JSONMemoryStore(self.sessions_dir / f"{slugify(session_id)}.json", scope="session")
