def mcp_tool_to_openrouter(tool):

    # `tool` is an MCP tool object returned by client.list_tools().
    # OpenRouter expects each tool in this function-calling format.
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            # inputSchema describes what arguments the tool accepts.
            "parameters": tool.inputSchema
        }
    }
