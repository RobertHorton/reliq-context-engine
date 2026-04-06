from pathlib import Path

from reliq_context_engine.cognition import UnifiedCognitionLayer
from reliq_context_engine.context_engine import ContextEngine
from reliq_context_engine.models import MemoryItem, TaskSpec


def seed_engine(tmp_path: Path) -> ContextEngine:
    wiki_dir = tmp_path / "knowledge" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "PromptInput.md").write_text(
        "# PromptInput\n\n## Description\nControlled React input component for prompts.\n\n## Related\n- VideoPreview\n",
        encoding="utf-8",
    )
    (wiki_dir / "SystemTheme.md").write_text(
        "# System Theme\n\nUse dark UI surfaces and preserve component consistency across releases.\n",
        encoding="utf-8",
    )
    memory_dir = tmp_path / "memory"
    return ContextEngine(wiki_dir=wiki_dir, memory_dir=memory_dir, knowledge_limit=5, memory_limit=5)


def test_context_engine_uses_wiki_and_memory(tmp_path: Path) -> None:
    engine = seed_engine(tmp_path)
    engine.memory.add(
        MemoryItem(
            content="User prefers dark UI and controlled form components.",
            kind="preference",
            scope="user",
            tags=["ui", "preferences"],
            importance=0.9,
        )
    )

    context = engine.build_context(TaskSpec(task="Create a dark prompt input component", type="ui"))

    assert context.knowledge
    assert context.memory
    prompt = engine.build_prompt(TaskSpec(task="Create a dark prompt input component", type="ui"))
    assert "RETRIEVED KNOWLEDGE" in prompt
    assert "RELEVANT MEMORY" in prompt
    assert "Scope: user" in prompt


def test_multi_scope_memory_prefers_exact_scope_over_shared_scope(tmp_path: Path) -> None:
    engine = seed_engine(tmp_path)
    engine.memory.add(
        MemoryItem(
            content="Use dark theme by default.",
            kind="preference",
            scope="user",
            key="theme",
            user_id="robert",
            tags=["ui"],
            importance=0.7,
        )
    )
    engine.memory.add(
        MemoryItem(
            content="Use dark theme and compact spacing for this active session.",
            kind="session_state",
            scope="session",
            key="theme",
            user_id="robert",
            session_id="sess-1",
            tags=["ui"],
            importance=1.0,
        )
    )
    engine.memory.add(
        MemoryItem(
            content="System standard is neutral theme.",
            kind="system_update",
            scope="system",
            key="theme",
            tags=["ui"],
            importance=0.5,
        )
    )

    results = engine.memory.search(
        TaskSpec(task="build dark ui", type="ui", user_id="robert", session_id="sess-1"),
        limit=3,
    )

    assert results
    assert results[0].scope == "session"
    assert "compact spacing" in results[0].content


def test_multi_scope_memory_falls_back_without_leaking_unrelated_scope(tmp_path: Path) -> None:
    engine = seed_engine(tmp_path)
    engine.memory.add(
        MemoryItem(
            content="User prefers terminal-style diagnostics summaries.",
            kind="preference",
            scope="user",
            user_id="robert",
            tags=["diagnostics"],
            importance=0.9,
        )
    )
    engine.memory.add(
        MemoryItem(
            content="Other session prefers animated UI previews.",
            kind="session_state",
            scope="session",
            session_id="other-session",
            user_id="robert",
            tags=["ui"],
            importance=1.0,
        )
    )

    results = engine.memory.search(
        TaskSpec(task="diagnose pm2 logs", type="diagnostics", user_id="robert", session_id="sess-2"),
        limit=3,
    )

    assert results
    assert all(item.session_id != "other-session" for item in results if item.scope == "session")
    assert any(item.scope == "user" for item in results)


def test_context_injection_is_deterministic_and_minimal(tmp_path: Path) -> None:
    engine = seed_engine(tmp_path)
    for idx in range(6):
        engine.memory.add(
            MemoryItem(
                content=f"Dark UI preference note {idx}",
                kind="preference",
                scope="user",
                key=f"pref-{idx}",
                tags=["ui"],
                importance=0.5 + (idx * 0.05),
            )
        )

    task = TaskSpec(task="Create a dark prompt input component", type="ui")
    prompt_one = engine.build_prompt(task)
    prompt_two = engine.build_prompt(task)
    prompt_from_context = engine.build_prompt_from_context(engine.build_context(task))

    assert prompt_one == prompt_two
    assert prompt_one == prompt_from_context
    assert prompt_one.count("RELEVANT MEMORY") == 1
    assert prompt_one.count("[1]") >= 2


def test_unified_cognition_flow_combines_retrieval_memory_and_notes(tmp_path: Path) -> None:
    engine = seed_engine(tmp_path)
    layer = UnifiedCognitionLayer(context_engine=engine)
    result = layer.run_cognition(
        "We built a dark prompt input component for the dashboard.",
        task_type="ui",
        user_id="robert",
        session_id="sess-3",
        runner=lambda prompt: "Implemented the component and kept the dark theme consistent.",
        persist=True,
    )

    assert result.context.knowledge
    assert "TASK" in result.prompt
    assert result.response is not None
    assert result.memory_updates
    snapshot = engine.memory.get_memory(user_id="robert", session_id="sess-3")
    assert any(name.startswith("session") and items for name, items in snapshot.items())
    assert snapshot["system"]
