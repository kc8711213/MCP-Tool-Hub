# MCP Tool Hub

`MCP Tool Hub` is a generic middle-layer MCP server that sits between an LLM client and multiple downstream MCP servers.

Instead of exposing every downstream tool schema directly to the model, the hub keeps the assistant-facing surface small and stable:

- `search_tools`
- `invoke_tool`
- `list_registered_tools`

This reduces prompt bloat, keeps tool discovery targeted, and makes multi-server MCP setups easier to manage.

## Why This Exists

When an LLM client connects to many MCP servers at once, every tool schema can end up competing for prompt space.

That creates a few practical problems:

- larger system prompts
- noisier tool selection
- weaker reasoning efficiency
- harder scaling as more MCP servers are added

The hub addresses that by moving discovery and routing into a single MCP server.

## How It Works

The hub connects to downstream MCP servers over `stdio`, registers their tools internally, and exposes only three top-level tools to the client:

- `search_tools(query, top_k=5)`
  - Find the most relevant downstream tools for a request.
- `invoke_tool(tool_id, arguments)`
  - Call a downstream tool once the exact tool is known.
- `list_registered_tools(server_id=None)`
  - Inspect registered tools for debugging or explicit enumeration.

Tool IDs are normalized as:

```text
{server_id}.{tool_name}
```

Example:

```text
local-rag.query_documents
```

## Search Strategy

The built-in registry uses lightweight weighted matching across:

- tool name
- tags
- description

Default weights:

- `name`: `+3`
- `tags`: `+2`
- `description`: `+1`

`search_tools` also returns a `usage_instruction` field to guide the client toward `invoke_tool(...)`.

## Project Structure

```text
src/tool_hub/
  __init__.py
  clients.py
  config.py
  hub_server.py
  models.py
  real_client_v2.py
  registry.py

config.example.yaml
config.yaml          # local-only, ignored by git
run_hub.py
pyproject.toml
```

## Installation

```bash
pip install -e .
```

For local testing:

```bash
pip install -e .[dev]
```

## Quick Start

Start with the included example config:

```bash
mcp-tool-hub --config config.example.yaml
```

Or run through the lightweight wrapper:

```bash
python run_hub.py --config config.example.yaml
```

You can also provide the config path through an environment variable:

```bash
set TOOL_HUB_CONFIG=config.example.yaml
python run_hub.py
```

## Configuration

Example config:

```yaml
mock_mode: true
default_tool_tags:
  - mcp
  - hub

servers:
  - id: demo-files
    command: python
    args: ["demo_server.py"]
    env:
      ENV: dev
```

Notes:

- `mock_mode: true` is useful for local smoke testing.
- `mock_mode: false` enables real downstream MCP connections.
- downstream processes intentionally inherit the hub working directory unless you explicitly change that behavior in code

## Real-World Validation

This project has already been exercised against a local RAG-style downstream MCP server:

- downstream server launched through the hub
- tools discovered and registered successfully
- local document ingestion executed through `invoke_tool`
- document queries returned results through the hub

That validates the core design: the hub is not limited to mocks and can route real MCP tool workflows end to end.

## Recommended Client Behavior

For best results, clients should follow this pattern:

1. Use `search_tools` when the correct downstream tool is not yet known.
2. Use `invoke_tool` once the exact tool has been identified.
3. Use `list_registered_tools` for inspection, debugging, or explicit user requests.

This keeps the hub generic and avoids hard-coding behavior for any single MCP domain such as RAG, browser tools, or developer utilities.

## Development Notes

- the real client bridge uses a dedicated event loop thread and `asyncio.run_coroutine_threadsafe(...)`
- downstream `stderr` is buffered so startup noise stays out of normal logs, while error output can still be surfaced on failures
- pytest temp output is pinned to `tests/.tmp` to avoid polluting the repo root

## Status

Current state:

- core hub runtime implemented
- mock mode implemented
- real stdio downstream client implemented
- config loading implemented
- registry search implemented
- local tests included

## License

No license has been added yet.
