from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from .cognition import UnifiedCognitionLayer
from .context_engine import ContextEngine
from .models import MemoryItem, TaskSpec

DEFAULT_TASKS = [
    {
        "task": "Create a dark themed prompt input component for the dashboard.",
        "type": "ui",
        "user_id": "benchmark-user",
        "session_id": "bench-ui",
    },
    {
        "task": "Diagnose a PM2 restart loop and suggest the most likely root cause.",
        "type": "diagnostics",
        "user_id": "benchmark-user",
        "session_id": "bench-diag",
    },
    {
        "task": "Implement a modular API wrapper for a local runtime provider.",
        "type": "code",
        "user_id": "benchmark-user",
        "session_id": "bench-code",
    },
]


def deterministic_runner(prompt: str) -> str:
    first_line = next((line.strip() for line in prompt.splitlines() if line.strip()), "TASK")
    return f"Implemented response for {first_line[:80]}"


def time_call(fn, *args, **kwargs) -> tuple[Any, float]:
    start = time.perf_counter()
    value = fn(*args, **kwargs)
    duration_ms = (time.perf_counter() - start) * 1000
    return value, round(duration_ms, 3)


def load_tasks(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return list(DEFAULT_TASKS)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def seed_wiki(wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    docs = {
        "UI.md": "# UI\n\nPrefer dark UI surfaces, controlled inputs, and consistent spacing.\n",
        "Diagnostics.md": "# Diagnostics\n\nCheck restart loops, recent logs, and configuration drift first.\n",
        "Runtime.md": "# Runtime\n\nProvider wrappers should stay modular and avoid direct model coupling.\n",
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
    ]
    for item in seeds:
        engine.memory.add(item)


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "avg_ms": round(statistics.mean(values), 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


def run_benchmark(tasks: list[dict[str, Any]], iterations: int = 3) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        wiki_dir = root / "knowledge" / "wiki"
        memory_dir = root / "memory"
        seed_wiki(wiki_dir)
        engine = ContextEngine(wiki_dir=wiki_dir, memory_dir=memory_dir, knowledge_limit=3, memory_limit=3)
        seed_memory(engine)
        layer = UnifiedCognitionLayer(context_engine=engine)

        timings = {
            "build_context_ms": [],
            "build_prompt_ms": [],
            "memory_search_ms": [],
            "process_interaction_ms": [],
            "run_cognition_ms": [],
        }
        per_task: list[dict[str, Any]] = []

        for _ in range(iterations):
            for raw_task in tasks:
                task = TaskSpec.from_any(raw_task)
                _, memory_ms = time_call(engine.memory.search, task, 3)
                context, context_ms = time_call(engine.build_context, task)
                prompt, prompt_ms = time_call(engine.build_prompt, task)
                cognition, cognition_ms = time_call(
                    layer.run_cognition,
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
                _, process_ms = time_call(engine.process_interaction, task.task, cognition.response, task)

                timings["memory_search_ms"].append(memory_ms)
                timings["build_context_ms"].append(context_ms)
                timings["build_prompt_ms"].append(prompt_ms)
                timings["run_cognition_ms"].append(cognition_ms)
                timings["process_interaction_ms"].append(process_ms)

                per_task.append(
                    {
                        "task": task.task,
                        "type": task.type,
                        "knowledge_hits": len(context.knowledge),
                        "memory_hits": len(context.memory),
                        "prompt_chars": len(prompt),
                        "response_chars": len(cognition.response or ""),
                        "timings_ms": {
                            "memory_search": memory_ms,
                            "build_context": context_ms,
                            "build_prompt": prompt_ms,
                            "run_cognition": cognition_ms,
                            "process_interaction": process_ms,
                        },
                    }
                )

        return {
            "iterations": iterations,
            "task_count": len(tasks),
            "summary": {name: summarize(values) for name, values in timings.items()},
            "tasks": per_task,
            "memory_files": {key: str(value) for key, value in engine.memory.paths.items()},
            "dataset_file": str(layer.evolution.path),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the Reliq Context Engine cognition flow.")
    parser.add_argument("--tasks-file", default=None, help="Optional JSON file with benchmark task specs.")
    parser.add_argument("--iterations", type=int, default=3, help="How many times to run each task.")
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
