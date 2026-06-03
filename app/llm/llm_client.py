import asyncio
import json

from app.llm.setup import client, llm
from app.llm.tool_converter import mcp_tool_to_openrouter


# Default question for manual local testing.
DEFAULT_QUESTION = "Find history books with rating above 4"


async def ask_agent(question: str) -> str:
    # Main flow:
    # 1. Ask MCP what tools exist.
    # 2. Give those tools to the LLM.
    # 3. If the LLM asks for a tool, run it.
    # 4. Send the tool result back to the LLM.
    # 5. Return the final answer as a string.
    async with client:

        # Step 1: ask the MCP server which tools are available.
        mcp_tools = await client.list_tools()

        # Step 2: convert MCP tool definitions into the format OpenRouter expects.
        openrouter_tools = [
            mcp_tool_to_openrouter(tool)
            for tool in mcp_tools
        ]

        # First LLM call: the model decides whether it can answer directly
        # or whether it should call one of the tools.
        response = llm.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    # `question` is the user's original request.
                    "role": "user",
                    "content": question
                }
            ],
            tools=openrouter_tools
        )

        # `message` is the model's first response.
        # It may contain either normal text or tool call instructions.
        message = response.choices[0].message

        if message.tool_calls:

            # For now, handle the first requested tool call only.
            tool_call = message.tool_calls[0]

            # Name of the MCP tool the model wants to run.
            tool_name = tool_call.function.name

            # Tool arguments come back as a JSON string, so convert them to a dict.
            arguments = json.loads(
                tool_call.function.arguments
            )

            print("\nTool Name:")
            print(tool_name)

            print("\nArguments:")
            print(arguments)

            # Run the MCP tool with the arguments chosen by the model.
            tool_result = await client.call_tool(
                tool_name,
                arguments
            )

            print("\nTool Result:")
            print(tool_result)

            # MCP returns text content, so extract that text before using it again.
            # In this project, that text is a JSON string.
            tool_text = tool_result.content[0].text

            # Convert the JSON string into Python data for debugging/inspection.
            tool_data = json.loads(
                tool_text
            )

            print("\nParsed Tool Data:")
            print(type(tool_data))
            print(tool_data[0])

            # Second LLM call: give the tool result back to the model so it can
            # turn raw tool output into a natural-language answer for the user.
            final_response = llm.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {
                        # System message = higher-level instruction for model behavior.
                        "role": "system",
                        "content":
                            "You are a helpful book assistant. "
                            "Use the tool results to answer the user."
                    },
                    {
                        "role": "user",
                        "content": question
                    },
                    {
                        # This reminds the model what action it took.
                        "role": "assistant",
                        "content":
                            f"I called the tool {tool_name}"
                    },
                    {
                        # Pass the raw tool output back so the model can summarize it.
                        "role": "user",
                        "content":
                            f"Tool returned:\n{tool_result.content[0].text}"
                    }
                ]
            )

            # Return only the final answer text because FastAPI/frontend code
            # usually needs a plain value, not print output.
            return (
                final_response
                .choices[0]
                .message
                .content
            )

        else:

            # If no tool is needed, return the model's direct answer.
            return message.content


async def main(question: str = DEFAULT_QUESTION):
    # This is only for local testing from terminal.
    answer = await ask_agent(question)
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
