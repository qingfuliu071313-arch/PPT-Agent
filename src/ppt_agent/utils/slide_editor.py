"""Single-slide editing: open existing PPTX, modify one slide, save.

Uses MCP Server to open and manipulate existing presentations.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class SlideEditor:
    """Edit individual slides in an existing PPTX file."""

    def __init__(self):
        self._server_params = StdioServerParameters(
            command="uvx",
            args=["--from", "office-powerpoint-mcp-server", "ppt_mcp_server"],
        )
        self._pres_id: str = ""

    def open_and_edit(self, pptx_path: str, slide_index: int,
                      operations: list[dict]) -> str:
        """Open a PPTX, apply operations to a specific slide, save.

        operations: list of dicts, each with 'tool' and 'args' keys.
        Example: [{"tool": "manage_text", "args": {"operation": "add", ...}}]
        """
        path = Path(pptx_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {pptx_path}")
        asyncio.run(self._edit_async(str(path), slide_index, operations))
        return str(path)

    async def _edit_async(self, pptx_path: str, slide_index: int,
                          operations: list[dict]) -> None:
        async with stdio_client(self._server_params) as streams:
            async with ClientSession(*streams) as s:
                await s.initialize()

                r = await self._call(s, "open_presentation", {"file_path": pptx_path})
                self._pres_id = r.get("presentation_id", "")

                for op in operations:
                    tool = op.get("tool", "")
                    args = op.get("args", {})
                    args["slide_index"] = slide_index
                    await self._call(s, tool, args)

                await self._call(s, "save_presentation", {"file_path": pptx_path})

    async def _call(self, s: ClientSession, tool: str, args: dict) -> dict:
        if self._pres_id and "presentation_id" not in args:
            args = {**args, "presentation_id": self._pres_id}
        result = await s.call_tool(tool, arguments=args)
        if result.content:
            for block in result.content:
                if hasattr(block, "text"):
                    try:
                        return json.loads(block.text)
                    except (json.JSONDecodeError, AttributeError):
                        return {"raw": block.text}
        return {}

    def get_slide_info(self, pptx_path: str, slide_index: int) -> dict:
        """Get information about a specific slide."""
        path = Path(pptx_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {pptx_path}")
        return asyncio.run(self._get_info_async(str(path), slide_index))

    async def _get_info_async(self, pptx_path: str, slide_index: int) -> dict:
        async with stdio_client(self._server_params) as streams:
            async with ClientSession(*streams) as s:
                await s.initialize()
                r = await self._call(s, "open_presentation", {"file_path": pptx_path})
                self._pres_id = r.get("presentation_id", "")
                return await self._call(s, "get_slide_info", {"slide_index": slide_index})

    def replace_slide(self, pptx_path: str, slide_index: int,
                      new_content: dict) -> str:
        """Replace a slide's content entirely.

        Deletes all shapes on the target slide and rebuilds with new_content.
        new_content should match SlideContent model structure.
        """
        from ppt_agent.models import SlideContent
        sc = SlideContent.model_validate(new_content)

        path = Path(pptx_path).resolve()
        asyncio.run(self._replace_async(str(path), slide_index, sc))
        return str(path)

    async def _replace_async(self, pptx_path: str, slide_index: int,
                             sc) -> None:
        from ppt_agent.pipeline.mcp_renderer import MCPRenderer
        from ppt_agent.models import Presentation, PresentationOutline, UserRequirement

        async with stdio_client(self._server_params) as streams:
            async with ClientSession(*streams) as s:
                await s.initialize()

                r = await self._call(s, "open_presentation", {"file_path": pptx_path})
                self._pres_id = r.get("presentation_id", "")

                info = await self._call(s, "get_presentation_info", {})
                total = info.get("slide_count", 0)

                renderer = MCPRenderer()
                renderer._pres_id = self._pres_id

                dummy_pres = Presentation(
                    requirement=UserRequirement(topic="edit"),
                    outline=PresentationOutline(title="", subtitle="", total_slides=total,
                                                narrative_arc="", slides=[]),
                    slides=[sc],
                )

                await renderer._dispatch(s, sc, dummy_pres, slide_index)

                await self._call(s, "save_presentation", {"file_path": pptx_path})
