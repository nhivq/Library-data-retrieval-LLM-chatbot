from fastmcp import Client
import asyncio
from app.mcp_integration.server import mcp

client = Client(mcp)

# MCP communication is asynchronous
async def main():

    async with client:
        result = await client.call_tool(
            "search_books",
            {
                "q": "history"
            }
        )

        print(result.content[0].text)

        tools = await client.list_tools()

        for tool in tools:
            print(tool)
            print(type(tool))


asyncio.run(main())