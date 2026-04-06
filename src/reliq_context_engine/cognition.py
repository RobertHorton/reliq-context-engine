from __future__ import annotations

from typing import Callable

from .context_engine import ContextEngine
from .evolution import EvolutionEngine
from .models import CognitionResult, TaskSpec

TASK_TYPE_HINTS = {
    "ui": ("ui", "component", "layout", "theme", "design"),
    "code": ("code", "api", "function", "module", "implement", "refactor"),
    "diagnostics": ("debug", "diagnose", "failure", "error", "issue", "logs"),
    "vision": ("screen", "image", "vision", "browser", "screenshot"),
    "memory": ("memory", "context", "knowledge", "history"),
    "video": ("video", "clip", "scene", "render"),
}


def infer_task_type(user_input: str) -> str:
    lowered = user_input.lower()
    for task_type, hints in TASK_TYPE_HINTS.items():
        if any(hint in lowered for hint in hints):
            return task_type
    return "general"


class UnifiedCognitionLayer:
    def __init__(self, context_engine: ContextEngine | None = None, evolution_engine: EvolutionEngine | None = None) -> None:
        self.context_engine = context_engine or ContextEngine()
        self.evolution = evolution_engine or EvolutionEngine()

    def run_cognition(
        self,
        user_input: str,
        runner: Callable[[str], str] | None = None,
        task_type: str | None = None,
        target: str | None = None,
        constraints: list[str] | None = None,
        metadata: dict | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        persist: bool = True,
    ) -> CognitionResult:
        task = TaskSpec(
            task=user_input,
            type=task_type or infer_task_type(user_input),
            target=target,
            user_id=user_id,
            session_id=session_id,
            constraints=constraints or [],
            metadata=metadata or {},
        )
        context = self.context_engine.build_context(task)
        prompt = self.context_engine.build_prompt(task)
        response = runner(prompt) if runner is not None else None
        memory_updates = self.context_engine.process_interaction(user_input, response, task) if persist else []
        evolution_logged = self.evolution.evolution_step(prompt, response, task=task) if response else False
        return CognitionResult(
            task=task,
            context=context,
            prompt=prompt,
            response=response,
            memory_updates=memory_updates,
            evolution_logged=evolution_logged,
        )
