import asyncio
import os
import json

from dotenv import load_dotenv
from openai import OpenAI
from fastmcp import Client

from app.mcp_integration.server import mcp

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")


# ---------- OpenRouter ----------
llm = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)


# ---------- MCP Client ----------
client = Client(mcp)


# ---------- Convert MCP Tool to OpenRouter Tool ----------
def mcp_tool_to_openrouter(tool):

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema
        }
    }


# ---------- Main ----------
async def main():

    async with client:

        # Get tools from MCP server and store them asynchronously
        mcp_tools = await client.list_tools()

        # Convert MCP tools into OpenRouter format
        openrouter_tools = [
            mcp_tool_to_openrouter(tool)
            for tool in mcp_tools
        ]

        user_question = (
                "Find history books with rating above 4"
            )
        
        # Ask LLM
        response = llm.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": user_question
                }
            ],
            tools=openrouter_tools
        )

        # Get LLM response
        # Extract the first choice's message object and assign to message
        message = response.choices[0].message

        # Check whether LLM wants a tool
        if message.tool_calls:

            tool_call = message.tool_calls[0]

            tool_name = tool_call.function.name

            arguments = json.loads(
                tool_call.function.arguments
            )

            print("\nTool Name:")
            print(tool_name)

            print("\nArguments:")
            print(arguments)

            # Execute MCP tool
            tool_result = await client.call_tool(
                tool_name,
                arguments
            )

            print("\nTool Result:")
            print(tool_result)

             # Extract JSON string from MCP response
            tool_text = tool_result.content[0].text

            # Convert JSON string -> Python list
            tool_data = json.loads(
                tool_text
            )
            
            print("\nParsed Tool Data:")
            print(type(tool_data))
            print(tool_data[0])


            # ---------- Second LLM Call ----------
            # Give tool result back to LLM
            final_response = llm.chat.completions.create(
                model="openai/gpt-4o-mini",

                messages=[
                    {
                        "role": "system",
                        "content":
                            "You are a helpful book assistant. "
                            "Use the tool results to answer the user."
                    },

                    {
                        "role": "user",
                        "content": user_question
                    },

                    {
                        "role": "assistant",
                        "content":
                            f"I called the tool {tool_name}"
                    },

                    {
                        "role": "user",
                        "content":
                            f"Tool returned:\n{tool_result.content[0].text}"
                    }
                ]
            )
            print("\nFinal Answer:")

            print(
                final_response
                .choices[0]
                .message
                .content
            )

        else:

            print("No tool call requested")

            print(message.content)


asyncio.run(main())