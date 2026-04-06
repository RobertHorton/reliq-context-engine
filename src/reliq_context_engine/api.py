from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from .cognition import UnifiedCognitionLayer
from .context_engine import ContextEngine
from .models import MemoryItem, TaskSpec

app = FastAPI(title="Reliq Context Engine", version="0.2.0")
engine = ContextEngine()
ucl = UnifiedCognitionLayer(context_engine=engine)


class TaskRequest(BaseModel):
    task: str
    type: str = "general"
    target: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    constraints: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryRequest(BaseModel):
    content: str
    kind: str = "semantic"
    scope: str = "user"
    key: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    importance: float = 0.5


class InteractionRequest(BaseModel):
    user_input: str
    response: str | None = None
    task: str | None = None
    type: str = "general"
    target: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    constraints: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _task_spec(request: TaskRequest) -> TaskSpec:
    return TaskSpec(
        task=request.task,
        type=request.type,
        target=request.target,
        user_id=request.user_id,
        session_id=request.session_id,
        constraints=request.constraints,
        metadata=request.metadata,
    )


def _interaction_task(request: InteractionRequest) -> TaskSpec:
    return TaskSpec(
        task=request.task or request.user_input,
        type=request.type,
        target=request.target,
        user_id=request.user_id,
        session_id=request.session_id,
        constraints=request.constraints,
        metadata=request.metadata,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/context/build")
def context_build(request: TaskRequest) -> dict[str, Any]:
    built = engine.build_context(_task_spec(request))
    return built.to_dict()


@app.post("/context/prompt")
def context_prompt(request: TaskRequest) -> dict[str, str]:
    prompt = engine.build_prompt(_task_spec(request))
    return {"prompt": prompt}


@app.post("/cognition/run")
def cognition_run(request: TaskRequest) -> dict[str, Any]:
    result = ucl.run_cognition(
        request.task,
        task_type=request.type,
        target=request.target,
        constraints=request.constraints,
        metadata=request.metadata,
        user_id=request.user_id,
        session_id=request.session_id,
        persist=False,
    )
    return result.to_dict()


@app.post("/memory/items")
def create_memory(request: MemoryRequest) -> dict[str, Any]:
    item = engine.memory.add(
        MemoryItem(
            content=request.content,
            kind=request.kind,
            scope=request.scope,
            key=request.key,
            user_id=request.user_id,
            session_id=request.session_id,
            tags=request.tags,
            metadata=request.metadata,
            importance=request.importance,
        )
    )
    return item.to_dict()


@app.post("/memory/process")
def process_memory(request: InteractionRequest) -> dict[str, Any]:
    task = _interaction_task(request)
    items = engine.process_interaction(request.user_input, request.response, task)
    return {"results": [item.to_dict() for item in items]}


@app.get("/memory/search")
def search_memory(
    task: str = Query(...),
    task_type: str = Query("general"),
    user_id: str | None = Query(None),
    session_id: str | None = Query(None),
    limit: int = Query(3, ge=1, le=25),
) -> dict[str, Any]:
    task_spec = TaskSpec(task=task, type=task_type, user_id=user_id, session_id=session_id)
    return {"results": [item.to_dict() for item in engine.memory.search(task_spec, limit=limit)]}


@app.get("/memory/snapshot")
def memory_snapshot(
    scope: str | None = Query(None),
    user_id: str | None = Query(None),
    session_id: str | None = Query(None),
) -> dict[str, Any]:
    return engine.memory.get_memory(scope=scope, user_id=user_id, session_id=session_id)


@app.post("/memory/prune")
def prune_memory(limit_per_scope: int = Query(100, ge=1, le=1000)) -> dict[str, Any]:
    return engine.memory.prune_memory(limit_per_scope=limit_per_scope)


@app.get("/memory/file")
def memory_file() -> dict[str, Any]:
    return {"paths": {key: str(value) for key, value in engine.memory.paths.items()}}
