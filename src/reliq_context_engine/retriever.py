from __future__ import annotations

import json
import math
import re
from pathlib import Path

from .models import KnowledgeHit, TaskSpec

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

TASK_PROFILES = {
    "ui": "ui component design react styling interface",
    "video": "video generation pipeline scene animation render",
    "diagnostics": "debug diagnose logs failure root cause",
    "code": "code implementation api function module integration",
    "memory": "memory retrieval context knowledge history",
    "vision": "screen ui image browser visual state",
}


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9_\\-]{3,}", text.lower())
        if token not in STOPWORDS
    }


def task_query(task: TaskSpec) -> str:
    profile = TASK_PROFILES.get(task.type, "")
    parts = [task.task, task.type, task.target or "", profile]
    return " ".join(part for part in parts if part)


class WikiRetriever:
    def __init__(self, wiki_dir: str | Path) -> None:
        self.wiki_dir = Path(wiki_dir)

    def search(self, task: TaskSpec | str, limit: int = 3) -> list[KnowledgeHit]:
        task_spec = TaskSpec.from_any(task)
        query = task_query(task_spec)
        query_tokens = tokenize(query)
        if not self.wiki_dir.exists():
            return []

        hits: list[KnowledgeHit] = []
        for path in sorted(self.wiki_dir.rglob("*.md")):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            title = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), path.stem)
            overlap = query_tokens.intersection(tokenize(text))
            if not overlap:
                continue
            score = len(overlap) / max(len(query_tokens), 1)
            if task_spec.target and task_spec.target.lower() in text.lower():
                score += 0.2
            snippet = text[:1200].strip()
            hits.append(
                KnowledgeHit(
                    title=title,
                    content=snippet,
                    source=str(path),
                    score=round(score, 4),
                    kind="wiki",
                )
            )
        return sorted(hits, key=lambda item: item.score, reverse=True)[:limit]


class FaissRetriever:
    def __init__(self, index_path: str | Path, metadata_path: str | Path, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.model_name = model_name
        self._faiss = None
        self._encoder = None
        self._index = None
        self._metadata = None

    def _ready(self) -> bool:
        if not self.index_path.exists() or not self.metadata_path.exists():
            return False
        try:
            import faiss  # type: ignore
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception:
            return False

        if self._index is None:
            self._faiss = faiss
            self._encoder = SentenceTransformer(self.model_name)
            self._index = faiss.read_index(str(self.index_path))
            self._metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        return True

    def search(self, task: TaskSpec | str, limit: int = 3) -> list[KnowledgeHit]:
        task_spec = TaskSpec.from_any(task)
        if not self._ready():
            return []
        query = task_query(task_spec)
        vector = self._encoder.encode([query], normalize_embeddings=True)
        distances, indices = self._index.search(vector, limit)
        hits: list[KnowledgeHit] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue
            item = self._metadata[idx]
            score = max(0.0, 1.0 - float(dist))
            hits.append(
                KnowledgeHit(
                    title=item.get("title", f"chunk-{idx}"),
                    content=item.get("content", ""),
                    source=item.get("source", "faiss"),
                    score=round(score, 4),
                    kind="faiss",
                    metadata={key: value for key, value in item.items() if key not in {"title", "content", "source"}},
                )
            )
        return hits


class HybridRetriever:
    def __init__(self, wiki_dir: str | Path, faiss_index: str | Path | None = None, faiss_metadata: str | Path | None = None) -> None:
        self.wiki = WikiRetriever(wiki_dir)
        self.faiss = (
            FaissRetriever(faiss_index, faiss_metadata)
            if faiss_index and faiss_metadata
            else None
        )

    def search(self, task: TaskSpec | str, limit: int = 3) -> list[KnowledgeHit]:
        task_spec = TaskSpec.from_any(task)
        hits: dict[str, KnowledgeHit] = {}
        for item in self.wiki.search(task_spec, limit=max(limit, 5)):
            hits[f"wiki::{item.source}"] = item
        if self.faiss is not None:
            for item in self.faiss.search(task_spec, limit=max(limit, 5)):
                key = f"faiss::{item.source}::{item.title}"
                if key in hits:
                    hits[key].score = round(max(hits[key].score, item.score), 4)
                else:
                    hits[key] = item

        ranked = sorted(
            hits.values(),
            key=lambda item: (item.score, 0.1 if item.kind == "faiss" else 0.0, math.log(len(item.content) + 1)),
            reverse=True,
        )
        return ranked[:limit]
