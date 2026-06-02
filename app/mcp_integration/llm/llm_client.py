import asyncio
import json

from app.mcp_integration.llm.setup import client, llm
from app.mcp_integration.llm.tool_converter import mcp_tool_to_openrouter


DEFAULT_QUESTION = "Find history books with rating above 4"


async def ask_agent(question: str) -> str:
    async with client:

        mcp_tools = await client.list_tools()

        openrouter_tools = [
            mcp_tool_to_openrouter(tool)
            for tool in mcp_tools
        ]

        response = llm.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": question
                }
            ],
            tools=openrouter_tools
        )

        message = response.choices[0].message

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

            tool_result = await client.call_tool(
                tool_name,
                arguments
            )

            print("\nTool Result:")
            print(tool_result)

            tool_text = tool_result.content[0].text

            tool_data = json.loads(
                tool_text
            )

            print("\nParsed Tool Data:")
            print(type(tool_data))
            print(tool_data[0])

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
                        "content": question
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

            return (
                final_response
                .choices[0]
                .message
                .content
            )

        else:

            return message.content


async def main(question: str = DEFAULT_QUESTION):
    answer = await ask_agent(question)
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
