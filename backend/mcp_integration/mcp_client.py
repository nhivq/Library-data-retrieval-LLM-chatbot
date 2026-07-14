import asyncio
import logging

from fastmcp import Client
from backend.app.mcp_integration.server import mcp

logger = logging.getLogger(__name__)

client = Client(mcp)

async def main():
    """Small manual smoke test for MCP tool calls and tool listing."""

    async with client:
        result = await client.call_tool(
            "search_books",
            {
                "q": "history"
            }
        )

        logger.info(
            "MCP tool call completed",
            extra={"event": "mcp_tool_call", "tool_text": result.content[0].text},
        )

        tools = await client.list_tools()

        for tool in tools:
            logger.info(
                "MCP tool available",
                extra={"event": "mcp_tool_available", "tool_name": getattr(tool, "name", str(tool))},
            )


asyncio.run(main())
