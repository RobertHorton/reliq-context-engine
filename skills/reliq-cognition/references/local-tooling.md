# Local Tooling

## Canonical Files

- Master memory:
  - `C:\Projects\ClaudeZilla\data\memory\RELIQ-MASTER-MEMORY.md`
- Standalone context tool repo:
  - `C:\Projects\ClaudeZilla\reliq-context-engine`
- Main Reliq repo:
  - `C:\Projects\Reliq`

## Preferred Local Tool Surface

If available, use the local MCP server:

- `reliq-context-engine`

Useful operations:

- build context for a task
- build a deterministic prompt
- search scoped memory
- inspect current memory snapshot
- run the cognition entrypoint

## Repo Guidance

For `reliq-context-engine`:

- keep the flat Python module layout
- preserve wrapper surfaces: API, CLI, MCP
- do not merge knowledge retrieval and memory retrieval into one module

For `Reliq`:

- treat it as the destination platform repo
- move working behavior there only after it stabilizes in the standalone tool
