from __future__ import annotations

from typing import Any

from .cognition import UnifiedCognitionLayer
from .context_engine import ContextEngine
from .models import MemoryItem, TaskSpec

engine = ContextEngine()
ucl = UnifiedCognitionLayer(context_engine=engine)


def _task(
    task: str,
    task_type: str = "general",
    target: str | None = None,
    constraints: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> TaskSpec:
    return TaskSpec(
        task=task,
        type=task_type,
        target=target,
        user_id=user_id,
        session_id=session_id,
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
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Build minimal, task-specific context from wiki knowledge and structured memory."""
        built = engine.build_context(_task(task, task_type, target, constraints, metadata, user_id, session_id))
        return built.to_dict()

    @mcp.tool()
    def build_prompt(
        task: str,
        task_type: str = "general",
        target: str | None = None,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Build a deterministic prompt from task-specific knowledge and scoped memory."""
        return engine.build_prompt(_task(task, task_type, target, constraints, metadata, user_id, session_id))

    @mcp.tool()
    def run_cognition(
        user_input: str,
        task_type: str | None = None,
        target: str | None = None,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        persist: bool = False,
    ) -> dict[str, Any]:
        """Build the full cognition payload: task, context, prompt, and optional memory updates."""
        result = ucl.run_cognition(
            user_input,
            task_type=task_type,
            target=target,
            constraints=constraints,
            metadata=metadata,
            user_id=user_id,
            session_id=session_id,
            persist=persist,
        )
        return result.to_dict()

    @mcp.tool()
    def add_memory_item(
        content: str,
        kind: str = "semantic",
        scope: str = "user",
        key: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        importance: float = 0.5,
    ) -> dict[str, Any]:
        """Add a structured memory item to the engine's shared memory store."""
        item = engine.memory.add(
            MemoryItem(
                content=content,
                kind=kind,
                scope=scope,
                key=key,
                user_id=user_id,
                session_id=session_id,
                tags=tags or [],
                metadata=metadata or {},
                importance=importance,
            )
        )
        return item.to_dict()

    @mcp.tool()
    def process_interaction(
        user_input: str,
        response: str | None = None,
        task_type: str = "general",
        target: str | None = None,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extract and store structured memory after an interaction."""
        items = engine.process_interaction(
            user_input,
            response,
            _task(user_input, task_type, target, constraints, metadata, user_id, session_id),
        )
        return [item.to_dict() for item in items]

    @mcp.tool()
    def search_memory(
        task: str,
        task_type: str = "general",
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search scoped memory for items relevant to the current task."""
        results = engine.memory.search(_task(task, task_type, None, None, None, user_id, session_id))
        return [item.to_dict() for item in results]

    @mcp.tool()
    def get_memory(scope: str | None = None, user_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        """Return a snapshot of stored memory across one or more scopes."""
        return engine.memory.get_memory(scope=scope, user_id=user_id, session_id=session_id)

    @mcp.tool()
    def prune_memory(limit_per_scope: int = 100) -> dict[str, int]:
        """Prune lower-value memory items so the store remains small and relevant."""
        return engine.memory.prune_memory(limit_per_scope=limit_per_scope)

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
