from __future__ import annotations

import argparse
from functools import lru_cache
from typing import Any

from .clients import MCPClientManager
from .config import load_config
from .models import InvokeResult
from .registry import ToolRegistry


class ToolHubRuntime:
    def __init__(self, config_path: str | None = None) -> None:
        self.config = load_config(config_path)
        self.registry = ToolRegistry()
        self.client_manager = MCPClientManager(self.config)
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self.client_manager.start()
        self.registry.bulk_register(self.client_manager.list_registered_tools())
        self._started = True

    def search_tools(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        self.start()
        return [item.model_dump() for item in self.registry.search(query, top_k=top_k)]

    def list_registered_tools(
        self,
        server_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self.start()
        return [item.model_dump() for item in self.registry.list_tools(server_id)]

    def invoke_tool(self, tool_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.start()
        tool = self.registry.get(tool_id)
        result = self.client_manager.invoke_tool(tool_id, arguments)
        return InvokeResult(
            tool_id=tool.tool_id,
            server_id=tool.server_id,
            result=result,
        ).model_dump()

    def close(self) -> None:
        self.client_manager.close()


@lru_cache(maxsize=1)
def get_runtime(config_path: str | None = None) -> ToolHubRuntime:
    runtime = ToolHubRuntime(config_path)
    runtime.start()
    return runtime


def create_app(config_path: str | None = None) -> Any:
    try:
        from fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "FastMCP is required to run the hub server. Install project dependencies."
        ) from exc

    runtime = get_runtime(config_path)
    app = FastMCP(name="mcp-tool-hub")

    @app.tool()
    def search_tools(query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Find the most relevant downstream tools for a user request.

        Use this first when the correct downstream tool is not yet known from
        the current conversation. Prefer this over listing every tool when a
        targeted discovery step is sufficient.
        """
        return runtime.search_tools(query=query, top_k=top_k)

    @app.tool()
    def invoke_tool(tool_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke a downstream tool when the exact tool_id is already known.

        If the correct tool has not been identified yet, call search_tools
        first instead of guessing.
        """
        return runtime.invoke_tool(tool_id=tool_id, arguments=arguments)

    @app.tool()
    def list_registered_tools(
        server_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List registered downstream tools for inspection or explicit requests.

        Use this for debugging, auditing, or when the user explicitly asks to
        enumerate tools. Do not use it by default if search_tools can narrow
        the selection more efficiently.
        """
        return runtime.list_registered_tools(server_id=server_id)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MCP Tool Hub server.")
    parser.add_argument("--config", dest="config", help="Path to the hub YAML config.")
    args = parser.parse_args()

    app = create_app(args.config)
    app.run(transport="stdio", show_banner=False, log_level="ERROR")


if __name__ == "__main__":
    main()
