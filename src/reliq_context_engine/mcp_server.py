from __future__ import annotations

import json
from typing import Any

from .context_engine import ContextEngine
from .models import MemoryItem, TaskSpec

engine = ContextEngine()


def _task(task: str, task_type: str = "general", target: str | None = None, constraints: list[str] | None = None, metadata: dict[str, Any] | None = None) -> TaskSpec:
    return TaskSpec(
        task=task,
        type=task_type,
        target=target,
        constraints=constraints or [],
        metadata=metadata or {},
    )


def _register_tools(mcp: Any) -> None:
    @mcp.tool()
    def build_context(
        task: str,
        task_type: str = "general",
        target: str | None = None,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build minimal, task-specific context from wiki knowledge and structured memory."""
        built = engine.build_context(_task(task, task_type, target, constraints, metadata))
        return built.to_dict()

    @mcp.tool()
    def build_prompt(
        task: str,
        task_type: str = "general",
        target: str | None = None,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Build a deterministic prompt from task-specific knowledge and memory."""
        return engine.build_prompt(_task(task, task_type, target, constraints, metadata))

    @mcp.tool()
    def add_memory_item(
        content: str,
        kind: str = "semantic",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a structured memory item to the engine's shared memory store."""
        item = engine.memory.add(
            MemoryItem(
                content=content,
                kind=kind,
                tags=tags or [],
                metadata=metadata or {},
            )
        )
        return item.to_dict()

    @mcp.tool()
    def search_memory(task: str, task_type: str = "general") -> list[dict[str, Any]]:
        """Search structured memory for items relevant to the current task."""
        results = engine.memory.search(_task(task, task_type))
        return [item.to_dict() for item in results]

    @mcp.tool()
    def health() -> dict[str, str]:
        """Simple health check for the Reliq Context Engine MCP server."""
        return {"status": "ok"}


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover - import error path
        raise SystemExit(
            "The 'mcp' package is required to run the MCP server. "
            "Install dependencies from requirements.txt before starting this tool."
        ) from exc

    mcp = FastMCP("reliq-context-engine")
    _register_tools(mcp)
    mcp.run()


if __name__ == "__main__":
    main()
