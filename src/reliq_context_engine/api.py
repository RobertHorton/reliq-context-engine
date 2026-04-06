from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from .context_engine import ContextEngine
from .memory_integration import JSONMemoryStore
from .models import MemoryItem, TaskSpec

app = FastAPI(title="Reliq Context Engine", version="0.1.0")
engine = ContextEngine()


class TaskRequest(BaseModel):
    task: str
    type: str = "general"
    target: str | None = None
    constraints: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryRequest(BaseModel):
    content: str
    kind: str = "semantic"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _task_spec(request: TaskRequest) -> TaskSpec:
    return TaskSpec(
        task=request.task,
        type=request.type,
        target=request.target,
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


@app.post("/memory/items")
def create_memory(request: MemoryRequest) -> dict[str, Any]:
    item = engine.memory.add(
        MemoryItem(
            content=request.content,
            kind=request.kind,
            tags=request.tags,
            metadata=request.metadata,
        )
    )
    return item.to_dict()


@app.get("/memory/search")
def search_memory(task: str = Query(...), task_type: str = Query("general")) -> dict[str, Any]:
    task_spec = TaskSpec(task=task, type=task_type)
    return {"results": [item.to_dict() for item in engine.memory.search(task_spec)]}


@app.get("/memory/file")
def memory_file() -> dict[str, str]:
    return {"path": str(Path(engine.memory.path))}
