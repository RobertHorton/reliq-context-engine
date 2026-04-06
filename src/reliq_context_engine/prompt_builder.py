from __future__ import annotations

from .models import BuiltContext


DEFAULT_RULES = [
    "Use only the task-specific context provided below.",
    "Do not assume access to prior chat history.",
    "Prefer deterministic, minimal, and well-structured output.",
    "Do not restate irrelevant context.",
]


def build_prompt(context: BuiltContext, rules: list[str] | None = None) -> str:
    active_rules = rules or DEFAULT_RULES
    knowledge_block = "\n\n".join(
        f"[{idx}] {item.title}\nSource: {item.source}\nKind: {item.kind}\nScore: {item.score}\n{item.content}"
        for idx, item in enumerate(context.knowledge, start=1)
    ) or "None"
    memory_block = "\n\n".join(
        f"[{idx}] Kind: {item.kind}\nTags: {', '.join(item.tags) or 'none'}\nScore: {item.score}\n{item.content}"
        for idx, item in enumerate(context.memory, start=1)
    ) or "None"
    constraints = "\n".join(f"- {item}" for item in context.task.constraints) or "- None"
    rules_block = "\n".join(f"- {item}" for item in active_rules)

    return f"""TASK
Type: {context.task.type}
Target: {context.task.target or 'None'}
Instruction: {context.task.task}

CONSTRAINTS
{constraints}

RETRIEVED KNOWLEDGE
{knowledge_block}

RELEVANT MEMORY
{memory_block}

RULES
{rules_block}
"""
