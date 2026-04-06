from __future__ import annotations

import argparse
import json

from .context_engine import ContextEngine
from .models import TaskSpec


def main() -> None:
    parser = argparse.ArgumentParser(description="Build task-scoped context for Reliq or other AI systems.")
    parser.add_argument("--task", required=True, help="Natural-language task or instruction.")
    parser.add_argument("--task-type", default="general", help="Task category such as ui, code, diagnostics, video, memory, or vision.")
    parser.add_argument("--target", default=None, help="Optional target file, module, or system.")
    parser.add_argument("--constraint", action="append", default=[], help="Constraint to add. Repeat for multiple constraints.")
    parser.add_argument("--json", action="store_true", help="Emit built context as JSON instead of a prompt.")
    args = parser.parse_args()

    engine = ContextEngine()
    task = TaskSpec(task=args.task, type=args.task_type, target=args.target, constraints=args.constraint)
    if args.json:
        print(json.dumps(engine.build_context(task).to_dict(), indent=2))
        return
    print(engine.build_prompt(task))


if __name__ == "__main__":
    main()
