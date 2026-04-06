from pathlib import Path

from reliq_context_engine.context_engine import ContextEngine
from reliq_context_engine.memory_integration import JSONMemoryStore
from reliq_context_engine.models import MemoryItem, TaskSpec


def test_context_engine_uses_wiki_and_memory(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "knowledge" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "PromptInput.md").write_text(
        "# PromptInput\n\n## Description\nControlled React input component for prompts.\n\n## Related\n- VideoPreview\n",
        encoding="utf-8",
    )
    memory_path = tmp_path / "memory" / "memory.json"
    store = JSONMemoryStore(memory_path)
    store.add(
        MemoryItem(
            content="User prefers dark UI and controlled form components.",
            kind="semantic",
            tags=["ui", "preferences"],
        )
    )

    engine = ContextEngine(wiki_dir=wiki_dir, memory_file=memory_path)
    context = engine.build_context(TaskSpec(task="Create a dark prompt input component", type="ui"))

    assert context.knowledge
    assert context.memory
    prompt = engine.build_prompt(TaskSpec(task="Create a dark prompt input component", type="ui"))
    assert "RETRIEVED KNOWLEDGE" in prompt
    assert "RELEVANT MEMORY" in prompt
