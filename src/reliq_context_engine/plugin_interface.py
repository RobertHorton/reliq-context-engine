from __future__ import annotations

from .cognition import UnifiedCognitionLayer

_UCL = UnifiedCognitionLayer()


def run(input: str, task_type: str | None = None, user_id: str | None = None, session_id: str | None = None) -> dict:
    return _UCL.run_cognition(
        input,
        task_type=task_type,
        user_id=user_id,
        session_id=session_id,
        persist=True,
    ).to_dict()


def get_memory(scope: str | None = None, user_id: str | None = None, session_id: str | None = None) -> dict:
    return _UCL.context_engine.memory.get_memory(scope=scope, user_id=user_id, session_id=session_id)


def store_memory(input: str, output: str, task_type: str = "general", user_id: str | None = None, session_id: str | None = None) -> list[dict]:
    task = {
        "task": input,
        "type": task_type,
        "user_id": user_id,
        "session_id": session_id,
    }
    items = _UCL.context_engine.process_interaction(input, output, task)
    return [item.to_dict() for item in items]


def clear_memory(scope: str | None = None, user_id: str | None = None, session_id: str | None = None) -> dict[str, str]:
    _UCL.context_engine.memory.clear_memory(scope=scope, user_id=user_id, session_id=session_id)
    return {"status": "cleared"}


def prune_memory(limit_per_scope: int = 100) -> dict[str, int]:
    return _UCL.context_engine.memory.prune_memory(limit_per_scope=limit_per_scope)
