from fastmcp import Client
import asyncio

client = Client("server.py")

# MCP communication is asynchronous
async def main():

    async with client:

        tools = await client.list_tools()

        print(tools)


asyncio.run(main())