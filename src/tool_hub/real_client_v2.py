from __future__ import annotations

import asyncio
import tempfile
import threading
from concurrent.futures import Future
from typing import Any

from .models import DownstreamServerConfig, RegisteredTool


class RealMCPClient:
    """
    Best-effort real MCP client wrapper.

    The implementation keeps a dedicated event loop in a background thread and
    bridges synchronous hub calls through `asyncio.run_coroutine_threadsafe`.
    The actual MCP SDK imports are resolved lazily so the package can still be
    imported in environments that only need mock mode or static analysis.
    """

    def __init__(
        self,
        config: DownstreamServerConfig,
        default_tags: list[str] | None = None,
    ) -> None:
        self.config = config
        self.default_tags = default_tags or []
        self._errlog = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"mcp-client-{config.id}",
            daemon=True,
        )
        self._thread.start()
        self._session_ready = self._submit(self._connect()).result()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _submit(self, coroutine: Any) -> Future[Any]:
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    def _stderr_tail(self, max_chars: int = 4000) -> str:
        try:
            self._errlog.flush()
            self._errlog.seek(0)
            content = self._errlog.read()
            if not content:
                return ""
            return content[-max_chars:].strip()
        except Exception:
            return ""

    def _format_error(self, prefix: str, exc: Exception) -> RuntimeError:
        stderr_tail = self._stderr_tail()
        if stderr_tail:
            return RuntimeError(f"{prefix}: {exc}\n\nDownstream stderr tail:\n{stderr_tail}")
        return RuntimeError(f"{prefix}: {exc}")

    async def _connect(self) -> bool:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise RuntimeError(
                "Real MCP mode requires the 'mcp' package to be installed."
            ) from exc

        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=self.config.env or None,
        )

        try:
            self._stdio = stdio_client(server_params, errlog=self._errlog)
            self._read_stream, self._write_stream = await self._stdio.__aenter__()
            self._session = ClientSession(self._read_stream, self._write_stream)
            await self._session.__aenter__()
            await self._session.initialize()
            return True
        except Exception as exc:
            raise self._format_error(
                f"Failed to connect downstream MCP server '{self.config.id}'",
                exc,
            ) from exc

    def list_tools(self) -> list[RegisteredTool]:
        try:
            raw_tools = self._submit(self._list_tools_async()).result()
        except Exception as exc:
            raise self._format_error(
                f"Failed to list tools from downstream MCP server '{self.config.id}'",
                exc,
            ) from exc
        registered: list[RegisteredTool] = []
        for item in raw_tools:
            name = getattr(item, "name", "")
            description = getattr(item, "description", "") or ""
            input_schema = getattr(item, "inputSchema", None) or getattr(
                item, "input_schema", {}
            )
            metadata = getattr(item, "annotations", None) or {}
            tags = [*self.default_tags, *self.config.tags]
            registered.append(
                RegisteredTool(
                    tool_id=f"{self.config.id}.{name}",
                    server_id=self.config.id,
                    name=name,
                    description=description,
                    input_schema=input_schema or {},
                    tags=tags,
                    metadata={"sdk_annotations": metadata},
                )
            )
        return registered

    async def _list_tools_async(self) -> list[Any]:
        response = await self._session.list_tools()
        if hasattr(response, "tools"):
            return list(response.tools)
        return list(response)

    def invoke_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        try:
            return self._submit(self._invoke_tool_async(tool_name, arguments)).result()
        except Exception as exc:
            raise self._format_error(
                f"Failed to invoke downstream tool '{self.config.id}.{tool_name}'",
                exc,
            ) from exc

    async def _invoke_tool_async(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        response = await self._session.call_tool(tool_name, arguments)
        if hasattr(response, "content"):
            return response.content
        return response

    def close(self) -> None:
        try:
            self._submit(self._close_async()).result(timeout=5)
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)
            self._errlog.close()

    async def _close_async(self) -> None:
        if hasattr(self, "_session"):
            await self._session.__aexit__(None, None, None)
        if hasattr(self, "_stdio"):
            await self._stdio.__aexit__(None, None, None)
