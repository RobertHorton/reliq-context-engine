from __future__ import annotations

import re

from .memory_store import slugify
from .models import ExtractedMemory, TaskSpec

PREFERENCE_MARKERS = ("i like", "i prefer", "i want", "my preference", "i usually")
INTEREST_MARKERS = ("i'm building", "i am building", "i care about", "i'm interested in", "my goal is")
SYSTEM_MARKERS = ("we built", "we added", "we created", "we now have", "architecture", "repo", "system")
IMPLEMENTATION_MARKERS = ("implemented", "created", "added", "updated", "wired", "integrated", "published")


def summarize_text(text: str, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else f"{cleaned[: limit - 3].rstrip()}..."


def extract_memory(user_input: str, response: str | None = None, task: TaskSpec | str | None = None) -> list[ExtractedMemory]:
    task_spec = TaskSpec.from_any(task or user_input)
    lowered = user_input.lower()
    items: list[ExtractedMemory] = []

    items.append(
        ExtractedMemory(
            content=summarize_text(task_spec.task),
            scope="session",
            key="current_task",
            kind="session_state",
            tags=[task_spec.type, "current-task"],
            metadata={
                "target": task_spec.target,
                "constraints": task_spec.constraints,
            },
            user_id=task_spec.user_id,
            session_id=task_spec.session_id,
            importance=1.0,
        )
    )

    preference = _capture_marker_sentence(user_input, PREFERENCE_MARKERS)
    if preference:
        items.append(
            ExtractedMemory(
                content=preference,
                scope="user",
                key=f"preference:{slugify(preference)[:48]}",
                kind="preference",
                tags=[task_spec.type, "preferences"],
                metadata={"source": "user_input"},
                user_id=task_spec.user_id,
                session_id=task_spec.session_id,
                importance=0.95,
            )
        )

    interest = _capture_marker_sentence(user_input, INTEREST_MARKERS)
    if interest:
        items.append(
            ExtractedMemory(
                content=interest,
                scope="user",
                key=f"interest:{slugify(interest)[:48]}",
                kind="interest",
                tags=[task_spec.type, "interests"],
                metadata={"source": "user_input"},
                user_id=task_spec.user_id,
                session_id=task_spec.session_id,
                importance=0.8,
            )
        )

    if any(marker in lowered for marker in SYSTEM_MARKERS):
        items.append(
            ExtractedMemory(
                content=summarize_text(user_input),
                scope="system",
                key=f"system:{slugify(user_input)[:48]}",
                kind="system_update",
                tags=[task_spec.type, "system"],
                metadata={"source": "interaction"},
                user_id=task_spec.user_id,
                session_id=task_spec.session_id,
                importance=0.85,
            )
        )

    if response:
        response_summary = summarize_text(_first_meaningful_line(response))
        items.append(
            ExtractedMemory(
                content=response_summary,
                scope="session",
                key="last_response",
                kind="session_response",
                tags=[task_spec.type, "response"],
                metadata={"source": "assistant_output"},
                user_id=task_spec.user_id,
                session_id=task_spec.session_id,
                importance=0.6,
            )
        )
        if any(marker in response.lower() for marker in IMPLEMENTATION_MARKERS):
            items.append(
                ExtractedMemory(
                    content=response_summary,
                    scope="system",
                    key=f"implementation:{slugify(response_summary)[:48]}",
                    kind="implementation",
                    tags=[task_spec.type, "implementation"],
                    metadata={"source": "assistant_output"},
                    user_id=task_spec.user_id,
                    session_id=task_spec.session_id,
                    importance=0.75,
                )
            )

    return _dedupe(items)


def _capture_marker_sentence(text: str, markers: tuple[str, ...]) -> str | None:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    for sentence in sentences:
        lowered = sentence.lower()
        if any(marker in lowered for marker in markers):
            return summarize_text(sentence)
    return None


def _first_meaningful_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip(" -*\t")
        if cleaned:
            return cleaned
    return text


def _dedupe(items: list[ExtractedMemory]) -> list[ExtractedMemory]:
    deduped: dict[tuple[str, str | None, str], ExtractedMemory] = {}
    for item in items:
        key = (item.scope, item.key, item.content)
        current = deduped.get(key)
        if current is None or item.importance > current.importance:
            deduped[key] = item
    return list(deduped.values())
