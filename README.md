# Reliq Context Engine

Task-scoped context building for Reliq and other AI systems.

This repo is the better version of "context mode":
- no chat-history stuffing
- no prompt drift
- no giant context dumps
- explicit task -> retrieval -> memory -> prompt flow

## What It Does

Given a task, the engine:
1. normalizes it into a structured task spec
2. retrieves the most relevant knowledge from:
   - a wiki directory
   - an optional FAISS index
3. injects the most relevant memory items
4. builds a deterministic prompt from that context

Core principle:
- never send full chat history
- always rebuild minimal context for the current task

## Core Files

- [context_engine.py](src/reliq_context_engine/context_engine.py): orchestrates task -> context -> prompt
- [retriever.py](src/reliq_context_engine/retriever.py): hybrid FAISS + wiki retrieval
- [memory_integration.py](src/reliq_context_engine/memory_integration.py): structured memory store and search
- [prompt_builder.py](src/reliq_context_engine/prompt_builder.py): deterministic prompt construction
- [api.py](src/reliq_context_engine/api.py): FastAPI surface for other tools and plugins
- [cli.py](src/reliq_context_engine/cli.py): simple command-line entrypoint
- [mcp_server.py](src/reliq_context_engine/mcp_server.py): MCP server surface for direct tool use by Codex, Reliq, and other AI systems

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
- `memory/memory.json` for structured memory

These are used automatically if you do not set environment variables.

Optional semantic search dependencies:
- `faiss-cpu`
- `sentence-transformers`

Without them, the engine still works using wiki + keyword retrieval.

## Quick Start

```powershell
python -m reliq_context_engine.cli --task "Create a dark themed prompt input component" --task-type ui
```

## Run The API

```powershell
uvicorn reliq_context_engine.api:app --reload --host 127.0.0.1 --port 8041
```

Key endpoints:
- `POST /context/build`
- `POST /context/prompt`
- `POST /memory/items`
- `GET /memory/search`

## Environment Variables

- `RELIQ_KNOWLEDGE_WIKI`: path to wiki markdown files
- `RELIQ_FAISS_INDEX`: path to FAISS index file
- `RELIQ_FAISS_METADATA`: path to metadata JSON for FAISS chunks
- `RELIQ_MEMORY_FILE`: path to JSON memory store

## Plugin / Tool Surface

Other AI systems can use this in three ways:

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
- `add_memory_item`
- `search_memory`
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

If your MCP host starts servers from the repo root, the bundled `.mcp.json` works with the
default `knowledge/wiki` and `memory/memory.json` directories.

If you want to point the engine at an external Reliq knowledge base instead, copy
`mcp.json.example` and replace the placeholder paths with absolute paths for your machine.

## Design Rules

- Context must always be task-specific
- Context must be minimal
- Memory must be structured
- Retrieval should prefer top relevant results over broad dumps
- Chat history is not a primary context source

## Suggested Next Steps

- add FAISS chunk builder
- add more task-aware retrieval profiles
- add install scripts for Codex / Claude Desktop / other MCP hosts
