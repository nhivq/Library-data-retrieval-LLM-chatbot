import asyncio
import json

from app.llm.setup import client, llm
from app.llm.tool_converter import mcp_tool_to_openrouter


# ---------- Local Testing ----------
DEFAULT_QUESTION = "Tell me about author P. Grandcoing."


# ---------- Agent ----------
async def ask_agent(question: str) -> str:
    # Main flow:
    # 1. Ask MCP what tools exist.
    # 2. Give those tools to the LLM.
    # 3. If the LLM asks for a tool, run it.
    # 4. Send the tool result back to the LLM.
    # 5. Return the final answer as a string.
    async with client:

        # Safety protection
        MAX_ITERATIONS = 10
        iteration = 0

        # Get MCP tools
        mcp_tools = await client.list_tools()

        openrouter_tools = [
            mcp_tool_to_openrouter(tool)
            for tool in mcp_tools
        ]

        # Conversation History
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful book assistant. "
                    "Use available tools whenever needed. "
                    "You may call multiple tools before answering."
                )
            },
            {
                "role": "user",
                "content": question
            }
        ]

        # ReAct Loop
        while True:

            iteration += 1

            if iteration > MAX_ITERATIONS:

                return "Maximum tool iterations reached"

            # Ask LLM what to do next
            response = llm.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=messages,
                tools=openrouter_tools
            )

            message = response.choices[0].message

            print(message.tool_calls)

            # No tool calls -> final answer
            if not message.tool_calls:

                return message.content

            # Execute all tool calls
            for tool_call in message.tool_calls:

                # Name of the MCP tool the model wants to run.
                tool_name = tool_call.function.name

                # Tool arguments come back as a JSON string, so convert them to a dict.
                arguments = json.loads(
                    tool_call.function.arguments
                )

                print("\nTool:")
                print(tool_name)

                print("\nArguments:")
                print(arguments)

                try:

                    # Execute MCP Tool
                    tool_result = await client.call_tool(
                        tool_name,
                        arguments
                    )

                    print("\nTool Result:")
                    print(tool_result)

                    if not tool_result.content:
                        tool_text = (
                            f"Tool {tool_name} "
                            f"returned no content."
                        )

                    else:

                        tool_text = (
                            tool_result.content[0].text
                        )

                    # Debugging only
                    try:

                        # Convert the JSON string into Python data for debugging/inspection.
                        tool_data = json.loads(
                            tool_text
                        )

                        print("\nParsed Tool Data:")
                        print(type(tool_data))
                        print(tool_data)

                    except Exception:

                        print(
                            "\nTool result is not JSON."
                        )

                    # Feed tool result back to LLM

                    messages.append(
                        {
                            "role": "assistant",
                            "content":(
                                f"Called tool "
                                f"{tool_name} "
                                f"with arguments "
                                f"{arguments}"
                            )
                        }
                    )

                    messages.append(
                        {
                            "role": "user",
                            "content":(
                                f"Tool returned:\n"
                                f"{tool_text}"
                                )
                        }
                    )

                except Exception as e:
                    print("\nTool Error:")
                    print(e)

                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"Tool {tool_name} "
                                f"failed with error:\n"
                                f"{str(e)}"
                            )
                        }
                    )


# Local Test
async def main(question: str = DEFAULT_QUESTION):

    # This is only for local testing from terminal.
    answer = await ask_agent(question)

    print("\n=== FINAL ANSWER ===\n")
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
