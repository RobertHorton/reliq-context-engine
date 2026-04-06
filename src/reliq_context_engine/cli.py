from __future__ import annotations

import argparse
import json

from .cognition import UnifiedCognitionLayer
from .context_engine import ContextEngine
from .models import TaskSpec


def main() -> None:
    parser = argparse.ArgumentParser(description="Build task-scoped context and scoped memory for Reliq or other AI systems.")
    parser.add_argument("--task", required=True, help="Natural-language task or instruction.")
    parser.add_argument("--task-type", default="general", help="Task category such as ui, code, diagnostics, video, memory, or vision.")
    parser.add_argument("--target", default=None, help="Optional target file, module, or system.")
    parser.add_argument("--user-id", default=None, help="Optional user identity for scoped memory.")
    parser.add_argument("--session-id", default=None, help="Optional session identity for scoped memory.")
    parser.add_argument("--constraint", action="append", default=[], help="Constraint to add. Repeat for multiple constraints.")
    parser.add_argument("--response", default=None, help="Optional model response to store back into memory.")
    parser.add_argument("--json", action="store_true", help="Emit built context as JSON instead of a prompt.")
    parser.add_argument("--cognition", action="store_true", help="Emit the full cognition payload (task, context, prompt, memory updates).")
    args = parser.parse_args()

    engine = ContextEngine()
    task = TaskSpec(
        task=args.task,
        type=args.task_type,
        target=args.target,
        user_id=args.user_id,
        session_id=args.session_id,
        constraints=args.constraint,
    )
    if args.cognition:
        layer = UnifiedCognitionLayer(context_engine=engine)
        result = layer.run_cognition(
            args.task,
            task_type=args.task_type,
            target=args.target,
            constraints=args.constraint,
            user_id=args.user_id,
            session_id=args.session_id,
            persist=bool(args.response),
            runner=(lambda _prompt: args.response) if args.response else None,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return
    if args.json:
        print(json.dumps(engine.build_context(task).to_dict(), indent=2))
        return
    prompt = engine.build_prompt(task)
    if args.response:
        engine.process_interaction(args.task, args.response, task)
    print(prompt)


if __name__ == "__main__":
    main()
