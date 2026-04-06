from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from .cognition import UnifiedCognitionLayer
from .context_engine import ContextEngine
from .models import BuiltContext, MemoryItem, TaskSpec
from .prompt_builder import build_prompt as build_prompt_from_context

DEFAULT_TASKS = [
    {
        "task": "Create a dark themed prompt input component for the dashboard.",
        "type": "ui",
        "target": "PromptInput.tsx",
        "constraints": [
            "controlled input",
            "minimal styling",
            "accessible labels",
        ],
        "metadata": {
            "framework": "react",
            "surface": "desktop",
        },
        "user_id": "benchmark-user",
        "session_id": "bench-ui",
    },
    {
        "task": "Diagnose a PM2 restart loop and suggest the most likely root cause.",
        "type": "diagnostics",
        "metadata": {
            "surface": "ops",
        },
        "user_id": "benchmark-user",
        "session_id": "bench-diag",
    },
    {
        "task": "Implement a modular API wrapper for a local runtime provider.",
        "type": "code",
        "metadata": {
            "surface": "runtime",
        },
        "user_id": "benchmark-user",
        "session_id": "bench-code",
    },
]

WARMUPS = 3


def deterministic_runner(prompt: str) -> str:
    first_line = next((line.strip() for line in prompt.splitlines() if line.strip()), "TASK")
    return f"Implemented response for {first_line[:80]}"


def load_tasks(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return list(DEFAULT_TASKS)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def seed_wiki(wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    docs = {
        "UI.md": "# UI\n\nPrefer dark UI surfaces, controlled inputs, consistent spacing, and accessible labels.\n",
        "Diagnostics.md": "# Diagnostics\n\nCheck restart loops, recent logs, process configuration, and environment drift first.\n",
        "Runtime.md": "# Runtime\n\nProvider wrappers should stay modular, provider-agnostic, and easy to test.\n",
        "Memory.md": "# Memory\n\nSession memory should override user memory when it is more specific.\n",
        "Prompting.md": "# Prompting\n\nKeep prompts deterministic, minimal, and grounded in retrieved context.\n",
    }
    for name, content in docs.items():
        (wiki_dir / name).write_text(content, encoding="utf-8")


def seed_memory(engine: ContextEngine) -> None:
    seeds = [
        MemoryItem(
            content="User prefers dark UI and concise technical output.",
            kind="preference",
            scope="user",
            key="ui-style",
            user_id="benchmark-user",
            tags=["ui", "style"],
            importance=0.9,
        ),
        MemoryItem(
            content="System runtime wrappers should remain provider-agnostic.",
            kind="system_update",
            scope="system",
            key="runtime-wrapper",
            tags=["runtime", "architecture"],
            importance=0.8,
        ),
        MemoryItem(
            content="Current session is focused on diagnostics and restart loops.",
            kind="session_state",
            scope="session",
            key="diagnostics-focus",
            user_id="benchmark-user",
            session_id="bench-diag",
            tags=["diagnostics"],
            importance=1.0,
        ),
        MemoryItem(
            content="Controlled inputs should preserve accessible labels and dark styling.",
            kind="implementation",
            scope="system",
            key="prompt-input-guideline",
            tags=["ui", "component"],
            importance=0.75,
        ),
        MemoryItem(
            content="The current code task is about modular runtime wrappers.",
            kind="session_state",
            scope="session",
            key="runtime-session",
            user_id="benchmark-user",
            session_id="bench-code",
            tags=["code", "runtime"],
            importance=0.95,
        ),
    ]
    for item in seeds:
        engine.memory.add(item)


def make_fixture() -> tuple[ContextEngine, UnifiedCognitionLayer]:
    root = Path(tempfile.mkdtemp(prefix="reliq-bench-"))
    wiki_dir = root / "knowledge" / "wiki"
    memory_dir = root / "memory"
    seed_wiki(wiki_dir)
    engine = ContextEngine(wiki_dir=wiki_dir, memory_dir=memory_dir, knowledge_limit=3, memory_limit=3)
    seed_memory(engine)
    return engine, UnifiedCognitionLayer(context_engine=engine)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(percentile(values, 0.95), 3),
        "avg_ms": round(statistics.mean(values), 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


def time_case(fn: Callable[[], Any]) -> tuple[Any, float]:
    start = time.perf_counter_ns()
    value = fn()
    duration_ms = (time.perf_counter_ns() - start) / 1_000_000
    return value, round(duration_ms, 3)


def benchmark_case(case: str, task: TaskSpec, iterations: int) -> dict[str, Any]:
    durations: list[float] = []
    knowledge_hits: list[int] = []
    memory_hits: list[int] = []
    prompt_chars: list[int] = []
    memory_updates: list[int] = []
    evolution_logged: list[bool] = []

    for attempt in range(WARMUPS + iterations):
        engine, layer = make_fixture()

        if case == "build_context":
            value, duration = time_case(lambda: engine.build_context(task))
            details = value
            prompt_len = None
            update_count = None
            evolved = None
        elif case == "build_prompt":
            value, duration = time_case(lambda: engine.build_prompt(task))
            details = engine.build_context(task)
            prompt_len = len(value)
            update_count = None
            evolved = None
        elif case == "prompt_from_context":
            context = engine.build_context(task)
            value, duration = time_case(lambda: build_prompt_from_context(context))
            details = context
            prompt_len = len(value)
            update_count = None
            evolved = None
        elif case == "memory_search":
            value, duration = time_case(lambda: engine.memory.search(task, 3))
            details = value
            prompt_len = None
            update_count = None
            evolved = None
        elif case == "memory_update":
            value, duration = time_case(lambda: engine.process_interaction(task.task, deterministic_runner(task.task), task))
            details = value
            prompt_len = None
            update_count = len(value)
            evolved = None
        elif case == "run_cognition.persist_false":
            value, duration = time_case(
                lambda: layer.run_cognition(
                    task.task,
                    deterministic_runner,
                    task.type,
                    task.target,
                    task.constraints,
                    task.metadata,
                    task.user_id,
                    task.session_id,
                    False,
                )
            )
            details = value.context
            prompt_len = len(value.prompt)
            update_count = len(value.memory_updates)
            evolved = value.evolution_logged
        elif case == "run_cognition.persist_true":
            value, duration = time_case(
                lambda: layer.run_cognition(
                    task.task,
                    deterministic_runner,
                    task.type,
                    task.target,
                    task.constraints,
                    task.metadata,
                    task.user_id,
                    task.session_id,
                    True,
                )
            )
            details = value.context
            prompt_len = len(value.prompt)
            update_count = len(value.memory_updates)
            evolved = value.evolution_logged
        else:
            raise ValueError(f"Unsupported benchmark case: {case}")

        if attempt < WARMUPS:
            continue

        durations.append(duration)
        if isinstance(details, BuiltContext):
            knowledge_hits.append(len(details.knowledge))
            memory_hits.append(len(details.memory))
        elif isinstance(details, list):
            knowledge_hits.append(0)
            memory_hits.append(len(details))
        else:
            knowledge_hits.append(0)
            memory_hits.append(0)
        if prompt_len is not None:
            prompt_chars.append(prompt_len)
        if update_count is not None:
            memory_updates.append(update_count)
        if evolved is not None:
            evolution_logged.append(evolved)

    notes = []
    if case == "build_prompt":
        notes.append("build_prompt measures retrieval plus prompt formatting from a task spec.")
    if case in {"run_cognition.persist_false", "run_cognition.persist_true"}:
        notes.append("run_cognition now reuses the previously built context when generating the prompt.")
    if case == "memory_search":
        notes.append("memory_search includes JSON write cost because access_count is persisted.")

    return {
        "case": case,
        "task_type": task.type,
        "iterations": iterations,
        **summarize(durations),
        "knowledge_hits": round(statistics.mean(knowledge_hits), 2) if knowledge_hits else 0,
        "memory_hits": round(statistics.mean(memory_hits), 2) if memory_hits else 0,
        "memory_updates": round(statistics.mean(memory_updates), 2) if memory_updates else 0,
        "prompt_chars": round(statistics.mean(prompt_chars), 2) if prompt_chars else 0,
        "evolution_logged": any(evolution_logged),
        "notes": notes,
    }


def make_table(rows: list[dict[str, Any]]) -> list[str]:
    lines = ["case | task_type | median_ms | p95_ms | knowledge_hits | memory_hits | memory_updates | prompt_chars"]
    for row in rows:
        lines.append(
            f"{row['case']} | {row['task_type']} | {row['median_ms']} | {row['p95_ms']} | "
            f"{row['knowledge_hits']} | {row['memory_hits']} | {row['memory_updates']} | {row['prompt_chars']}"
        )
    return lines


def run_benchmark(tasks: list[dict[str, Any]], iterations: int = 25) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for raw_task in tasks:
        task = TaskSpec.from_any(raw_task)
        for case in (
            "memory_search",
            "build_context",
            "prompt_from_context",
            "build_prompt",
            "memory_update",
            "run_cognition.persist_false",
            "run_cognition.persist_true",
        ):
            rows.append(benchmark_case(case, task, iterations))
    return {
        "warmups": WARMUPS,
        "iterations": iterations,
        "task_count": len(tasks),
        "results": rows,
        "table": make_table(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the Reliq Context Engine cognition flow.")
    parser.add_argument("--tasks-file", default=None, help="Optional JSON file with benchmark task specs.")
    parser.add_argument("--iterations", type=int, default=25, help="Measured iterations per case after warmup.")
    parser.add_argument("--output", default=None, help="Optional file path for JSON benchmark output.")
    args = parser.parse_args()

    results = run_benchmark(load_tasks(args.tasks_file), iterations=args.iterations)
    payload = json.dumps(results, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
