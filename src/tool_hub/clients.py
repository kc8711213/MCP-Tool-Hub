from __future__ import annotations

import logging
from typing import Any, Protocol

from .models import DownstreamServerConfig, HubConfig, RegisteredTool
from .real_client_v2 import RealMCPClient

logger = logging.getLogger(__name__)


class DownstreamClient(Protocol):
    def list_tools(self) -> list[RegisteredTool]:
        ...

    def invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        ...

    def close(self) -> None:
        ...


class MockDownstreamClient:
    def __init__(self, config: DownstreamServerConfig, default_tags: list[str]) -> None:
        self.config = config
        self.default_tags = default_tags

    def list_tools(self) -> list[RegisteredTool]:
        demo_tool = RegisteredTool(
            tool_id=f"{self.config.id}.health_check",
            server_id=self.config.id,
            name="health_check",
            description="Returns downstream server status.",
            tags=[*self.default_tags, *self.config.tags, "health"],
            metadata={"mock": True},
        )
        return [demo_tool]

    def invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        return {
            "tool_name": tool_name,
            "arguments": arguments,
            "server_id": self.config.id,
            "mock": True,
            "status": "ok",
        }

    def close(self) -> None:
        return None


class MCPClientManager:
    def __init__(self, config: HubConfig) -> None:
        self.config = config
        self._clients: dict[str, DownstreamClient] = {}

    def start(self) -> None:
        for server in self.config.servers:
            if not server.enabled:
                logger.info("Skipping disabled downstream server: %s", server.id)
                continue
            self._clients[server.id] = self._build_client(server)

    def _build_client(self, server: DownstreamServerConfig) -> DownstreamClient:
        if self.config.mock_mode:
            return MockDownstreamClient(server, self.config.default_tool_tags)
        return RealMCPClient(server, default_tags=self.config.default_tool_tags)

    def list_registered_tools(self) -> list[RegisteredTool]:
        tools: list[RegisteredTool] = []
        for client in self._clients.values():
            tools.extend(client.list_tools())
        return tools

    def invoke_tool(self, tool_id: str, arguments: dict[str, Any]) -> Any:
        server_id, tool_name = self._split_tool_id(tool_id)
        client = self._clients.get(server_id)
        if client is None:
            raise KeyError(f"No downstream client registered for server_id={server_id}")
        return client.invoke_tool(tool_name, arguments)

    def close(self) -> None:
        for client in self._clients.values():
            client.close()
        self._clients.clear()

    @staticmethod
    def _split_tool_id(tool_id: str) -> tuple[str, str]:
        if "." not in tool_id:
            raise ValueError(
                f"Invalid tool_id '{tool_id}'. Expected '<server_id>.<tool_name>'."
            )
        return tool_id.split(".", maxsplit=1)

