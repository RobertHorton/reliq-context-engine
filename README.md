# Reliq Context Engine

Task-scoped context, scoped memory, and a lightweight cognition layer for Reliq and other AI systems.

This repo is the better version of "context mode":
- no chat-history stuffing
- no prompt drift
- no giant context dumps
- explicit task -> retrieval -> memory -> prompt flow
- structured user / system / session memory
- reusable cognition and plugin surfaces

## What It Does

Given a task, the engine:
1. normalizes it into a structured task spec
2. retrieves the most relevant knowledge from:
   - a wiki directory
   - an optional FAISS index
3. injects the most relevant memory items
4. builds a deterministic prompt from that context
5. optionally stores memory updates and logs usable training/evolution traces

Core principle:
- never send full chat history
- always rebuild minimal context for the current task

## Core Files

- [context_engine.py](src/reliq_context_engine/context_engine.py): orchestrates task -> context -> prompt
- [retriever.py](src/reliq_context_engine/retriever.py): hybrid FAISS + wiki retrieval
- [memory_store.py](src/reliq_context_engine/memory_store.py): per-file and multi-scope memory persistence
- [memory_manager.py](src/reliq_context_engine/memory_manager.py): read/write control for user, system, and session memory
- [memory_extractor.py](src/reliq_context_engine/memory_extractor.py): heuristics for extracting durable signals from interactions
- [memory_retriever.py](src/reliq_context_engine/memory_retriever.py): scoped retrieval and ranking
- [memory_integration.py](src/reliq_context_engine/memory_integration.py): compatibility exports for memory primitives
- [prompt_builder.py](src/reliq_context_engine/prompt_builder.py): deterministic prompt construction
- [cognition.py](src/reliq_context_engine/cognition.py): unified cognition entrypoint for task -> context -> prompt -> optional memory updates
- [evolution.py](src/reliq_context_engine/evolution.py): lightweight dataset/evolution logging
- [plugin_interface.py](src/reliq_context_engine/plugin_interface.py): importable plugin surface for other AI systems
- [api.py](src/reliq_context_engine/api.py): FastAPI surface for other tools and plugins
- [cli.py](src/reliq_context_engine/cli.py): simple command-line entrypoint
- [mcp_server.py](src/reliq_context_engine/mcp_server.py): MCP server surface for direct tool use by Codex, Reliq, and other AI systems
- [resources/scheduler.py](src/reliq_context_engine/resources/scheduler.py): lightweight VRAM-aware scheduler and runtime status reader
- [dashboard/status.py](src/reliq_context_engine/dashboard/status.py): queue and history tracking for a local control surface
- [research/swarm.py](src/reliq_context_engine/research/swarm.py): scheduler-gated research swarm runner layered on top of cognition

## Repo Goals

This repo should be:
- a standalone Reliq ecosystem tool
- reusable as a plugin surface for other AI systems
- simple enough for Codex to extend safely

## Install

```powershell
cd C:\Projects\ClaudeZilla\reliq-context-engine
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Default local paths:
- `knowledge/wiki/` for markdown knowledge
- `memory/user.json` for shared user memory
- `memory/system.json` for shared system memory
- `memory/session.json` for default session memory
- `memory/users/*.json` for per-user scoped memory
- `memory/sessions/*.json` for per-session scoped memory
- `datasets/train.jsonl` for optional evolution logging

These are used automatically if you do not set environment variables.

Optional semantic search dependencies:
- `faiss-cpu`
- `sentence-transformers`

Without them, the engine still works using wiki + keyword retrieval.

## Quick Start

```powershell
python -m reliq_context_engine.cli --task "Create a dark themed prompt input component" --task-type ui
```

## Run A Benchmark

```powershell
python -m reliq_context_engine.benchmark `
  --tasks-file examples/benchmark_tasks.json `
  --iterations 25 `
  --output benchmark-results/latest.json
```

Or, after installing the package scripts:

```powershell
reliq-context-benchmark --iterations 25 --output benchmark-results/latest.json
```

Store response-derived memory in one pass:

```powershell
python -m reliq_context_engine.cli `
  --task "We built a dark prompt input component" `
  --task-type ui `
  --user-id robert `
  --session-id sess-1 `
  --response "Implemented the component and kept the dark theme consistent." `
  --cognition
```

## Run The API

```powershell
uvicorn reliq_context_engine.api:app --reload --host 127.0.0.1 --port 8041
```

Key endpoints:
- `POST /context/build`
- `POST /context/prompt`
- `POST /cognition/run`
- `GET /dashboard/status`
- `GET /dashboard/history`
- `POST /swarm/run`
- `POST /swarm/run-parallel`
- `POST /memory/items`
- `POST /memory/process`
- `GET /memory/search`
- `GET /memory/snapshot`

## Environment Variables

- `RELIQ_KNOWLEDGE_WIKI`: path to wiki markdown files
- `RELIQ_FAISS_INDEX`: path to FAISS index file
- `RELIQ_FAISS_METADATA`: path to metadata JSON for FAISS chunks
- `RELIQ_MEMORY_FILE`: path to JSON memory store
- `RELIQ_MEMORY_DIR`: path to the memory directory
- `RELIQ_DATASET_FILE`: path to the JSONL evolution log

## Plugin / Tool Surface

Other AI systems can use this in four ways:

1. Library

```python
from reliq_context_engine.context_engine import ContextEngine
```

2. HTTP API

```http
POST /context/prompt
```

3. MCP server

```powershell
python -m reliq_context_engine.mcp_server
```

4. CLI

```powershell
python -m reliq_context_engine.cli --task "debug pm2 restart loop" --task-type diagnostics
```

## MCP Tools

The MCP server exposes these tools:
- `build_context`
- `build_prompt`
- `run_cognition`
- `dashboard_status`
- `run_research_swarm`
- `add_memory_item`
- `process_interaction`
- `search_memory`
- `get_memory`
- `prune_memory`
- `health`

Example startup:

```powershell
python -m reliq_context_engine.mcp_server
```

Example MCP config:
- [mcp.json.example](mcp.json.example)
- [./.mcp.json](.mcp.json) for repo-local defaults

## Codex Plugin Support

This repo now includes:
- [./.mcp.json](.mcp.json): repo-local MCP server config
- [./.codex-plugin/plugin.json](.codex-plugin/plugin.json): Codex plugin metadata
- [./skills/reliq-cognition](skills/reliq-cognition): Codex skill for Reliq architecture and cognition workflow guidance

If your MCP host starts servers from the repo root, the bundled `.mcp.json` works with the
default `knowledge/wiki` and `memory/memory.json` directories.

If you want to point the engine at an external Reliq knowledge base instead, copy
`mcp.json.example` and replace the placeholder paths with absolute paths for your machine.

## Design Rules

- Context must always be task-specific
- Context must be minimal
- Memory must be structured and scoped
- Retrieval should prefer top relevant results over broad dumps
- Chat history is not a primary context source
- User preferences should survive across sessions
- Session memory should take precedence over shared memory when it is relevant

## Suggested Next Steps

- add FAISS chunk builder
- add more task-aware retrieval profiles
- add API and MCP smoke tests
- add websocket streaming for dashboard updates
- expand the research swarm from local cognition orchestration to true multi-agent ingestion/synthesis/validation roles
- add install scripts for Codex / Claude Desktop / other MCP hosts
