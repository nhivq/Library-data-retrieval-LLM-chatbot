def mcp_tool_to_openrouter(tool):

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema
        }
    }
