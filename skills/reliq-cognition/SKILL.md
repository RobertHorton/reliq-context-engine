---
name: "reliq-cognition"
description: "Use when working on Reliq architecture, the Reliq Context Engine, unified cognition flow, scoped memory, MCP integration, or when a task depends on context from C:\\Projects\\ClaudeZilla\\data\\memory\\RELIQ-MASTER-MEMORY.md, C:\\Projects\\ClaudeZilla\\reliq-context-engine, or C:\\Projects\\Reliq."
---

# Reliq Cognition

Use this skill for Reliq ecosystem work. The goal is to keep Codex aligned with the shipped Reliq architecture instead of defaulting to chat-history reasoning or ad hoc repo guesses.

## When To Use

- Work on Reliq, ClaudeZilla-to-Reliq migration, or the standalone context engine.
- Change context building, scoped memory, cognition flow, API wrappers, MCP tools, or plugin surfaces.
- Trace request flow across task -> context -> prompt -> execution -> memory update.
- Find the right repo or module for Reliq-related changes.

## Local Context

- Canonical memory: [RELIQ-MASTER-MEMORY.md](C:\Projects\ClaudeZilla\data\memory\RELIQ-MASTER-MEMORY.md)
- Standalone tool repo: [reliq-context-engine](C:\Projects\ClaudeZilla\reliq-context-engine)
- Main platform repo: [Reliq](C:\Projects\Reliq)

## Core Rules

1. Never use full chat history as the primary context source.
2. Rebuild task-specific context each time.
3. Prefer structured memory over conversation replay.
4. Keep changes modular and aligned with the existing repo shape.
5. Extend current modules before inventing parallel architectures.

## Workflow

1. Confirm which repo owns the change.
2. Read the relevant local doc or reference before editing.
3. If the local MCP server `reliq-context-engine` is available, prefer it for:
   - `build_context`
   - `build_prompt`
   - `run_cognition`
   - `search_memory`
   - `get_memory`
4. Preserve the cognition contract:
   - task-aware retrieval
   - scoped memory
   - deterministic prompt building
   - minimal context
5. For implementation work:
   - keep the flat Python module style in `reliq-context-engine`
   - keep knowledge retrieval separate from memory retrieval
   - keep session memory more specific than user memory, and user memory more specific than system memory

## Boundaries

- `reliq-context-engine` is the standalone cognition/context tool.
- `C:\Projects\Reliq` is the long-term platform home.
- `C:\Projects\ClaudeZilla\data\memory\RELIQ-MASTER-MEMORY.md` is the canonical project memory file.

## Reference Map

- `references/reliq-architecture.md`
- `references/local-tooling.md`

## Output Expectations

- Prefer concrete file changes over theory.
- Keep commits scoped to one architecture step when possible.
- For Reliq work, explain how the change affects context, memory, or cognition flow.
