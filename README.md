# MCP Tool Hub

`MCP Tool Hub` is a middle-layer MCP server that exposes a small stable tool surface to an LLM while dynamically managing tools from multiple downstream MCP servers.

## Goals

- Keep the assistant-facing tool schema small
- Discover tools through search instead of dumping every schema into prompt context
- Forward tool calls to downstream MCP servers through a single hub

## Exposed Tools

- `search_tools(query: str, top_k: int = 5)`
- `invoke_tool(tool_id: str, arguments: dict)`
- `list_registered_tools(server_id: str | None = None)`

## Project Layout

```text
src/tool_hub/
  config.py
  clients.py
  hub_server.py
  models.py
  real_client_v2.py
  registry.py
tests/
config.example.yaml
```

## Configuration

Set `TOOL_HUB_CONFIG` to a YAML file, or pass `--config` to the CLI.

Example:

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

The shipped example runs in `mock_mode` so the hub can be exercised without a real downstream MCP server. Set `mock_mode: false` for real stdio-backed MCP sessions.

The hub intentionally does not set a custom `cwd` for downstream processes. Child servers inherit the parent working directory so relative paths remain consistent for tools that expect them.

## Install

```bash
pip install -e .
```

For tests:

```bash
pip install -e .[dev]
```

## Run

```bash
mcp-tool-hub --config config.example.yaml
```

## Notes

- `search_tools` returns `usage_instruction` so the caller knows how to continue with `invoke_tool`.
- `tool_id` format is `{server_id}.{tool_name}`.
- Real downstream sessions are managed behind a small client abstraction. A mock mode is included for local testing.
