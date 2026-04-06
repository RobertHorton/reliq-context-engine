# Reliq Architecture

Reliq is a local-first AI orchestration platform.

Current relevant layers:

- Context Engine: task-scoped context building
- Knowledge Retrieval: wiki + optional FAISS
- Memory System: structured user, system, and session memory
- Unified Cognition Layer: task -> context -> prompt -> optional memory update
- MCP Surface: reusable tool entrypoint for Codex and other AI systems

Current standalone implementation repo:

- `C:\Projects\ClaudeZilla\reliq-context-engine`

Current long-term platform repo:

- `C:\Projects\Reliq`

Architectural rules:

1. No chat-history stuffing.
2. Use structured context.
3. Use scoped memory.
4. Keep knowledge retrieval separate from memory retrieval.
5. Prefer deterministic, minimal prompts.
6. Extend existing modules before creating competing abstractions.
