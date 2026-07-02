"""Thin async client for the Office-PowerPoint MCP render server.

Wraps session lifecycle (uvx-spawned stdio subprocess) and tool calls.
Tool-level errors are counted in `stats` so the renderer can report
degradation instead of silently producing an incomplete deck.
"""

from __future__ import annotations

import json
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:

    def __init__(self, server_params: StdioServerParameters):
        self._params = server_params
        self._session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None
        self.presentation_id: str = ""
        self.stats = {"tool_errors": 0, "degraded_shapes": 0}

    async def __aenter__(self) -> MCPClient:
        self._stack = AsyncExitStack()
        streams = await self._stack.enter_async_context(stdio_client(self._params))
        self._session = await self._stack.enter_async_context(ClientSession(*streams))
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc) -> None:
        await self._stack.aclose()

    async def call(self, tool: str, args: dict) -> dict:
        if self.presentation_id and "presentation_id" not in args:
            args = {**args, "presentation_id": self.presentation_id}
        result = await self._session.call_tool(tool, arguments=args)

        payload: dict = {}
        if result.content:
            for block in result.content:
                if hasattr(block, "text"):
                    try:
                        payload = json.loads(block.text)
                    except (json.JSONDecodeError, AttributeError):
                        payload = {"raw": block.text}
                    break
        if not isinstance(payload, dict):
            payload = {"raw": payload}

        if getattr(result, "isError", False) or payload.get("error"):
            self.stats["tool_errors"] += 1
        return payload
