from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import TaskSpec, utc_now


class EvolutionEngine:
    def __init__(self, dataset_file: str | Path | None = None) -> None:
        resolved = dataset_file or os.getenv("RELIQ_DATASET_FILE") or (Path.cwd() / "datasets" / "train.jsonl")
        self.path = Path(resolved)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def evaluate_output(self, output: str | None) -> bool:
        return bool(output and len(output.strip()) >= 20)

    def log_interaction(self, prompt: str, output: str, task: TaskSpec | None = None) -> None:
        payload: dict[str, Any] = {
            "timestamp": utc_now(),
            "prompt": prompt,
            "output": output,
        }
        if task is not None:
            payload["task"] = task.to_dict()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def evolution_step(self, prompt: str, output: str | None, task: TaskSpec | None = None) -> bool:
        if not self.evaluate_output(output):
            return False
        self.log_interaction(prompt, output or "", task=task)
        return True
