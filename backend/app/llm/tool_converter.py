def mcp_tool_to_openrouter(tool):
    """Convert a FastMCP tool description into OpenRouter function format."""

    # `tool` is an MCP tool object returned by client.list_tools().
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            # inputSchema describes what arguments the tool accepts.
            "parameters": tool.inputSchema
        }
    }
