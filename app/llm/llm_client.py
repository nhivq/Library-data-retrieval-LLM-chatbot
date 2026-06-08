import asyncio
import json
import time

from app.llm.setup import client, llm
from app.llm.tool_converter import mcp_tool_to_openrouter
from app.llm.memory import conversation_store


# ---------- Local Testing ----------
DEFAULT_QUESTION = "Delete all bookmarks of user 4. Then, save bookmark /works/OL10000112W for user 4 and then show all user 4's bookmarks"


# ---------- Agent ----------
async def ask_agent(
        question: str,
        session_id: str
) -> dict:
    # Main flow:
    # 1. Ask MCP what tools exist.
    # 2. Give those tools to the LLM.
    # 3. If the LLM asks for a tool, run it.
    # 4. Send the tool result back to the LLM.
    # 5. Return the final answer with progress metadata.
    async with client:

        # Safety protection
        MAX_ITERATIONS = 10
        iteration = 0
        progress = []

        progress.append("Assembling the AI agent and preparing tools...")

        # Get MCP tools
        mcp_tools = await client.list_tools()

        openrouter_tools = [
            mcp_tool_to_openrouter(tool)
            for tool in mcp_tools
        ]

        # Conversation History - Load existing or create new
        if session_id not in conversation_store:
            conversation_store[session_id] = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful book assistant with access to the app's real book data. "
                        "For any question about books, authors, ratings, tags, publication dates, bookmarks, or search results, use the available tools instead of answering from your own knowledge. "
                        "If you cannot find an answer in the tool output, say that the data is unavailable rather than inventing book titles, authors, ratings, or dates. "
                        "Do not hallucinate or fabricate books."
                    )
                }
            ]

        # Load existing history and append current question
        messages = conversation_store[session_id].copy()
        messages.append(
            {
                "role": "user",
                "content": question
            }
        )

        print("\n=== MEMORY ===")
        print(messages)

        # ReAct Loop
        while True:

            iteration += 1

            if iteration > MAX_ITERATIONS:
                progress.append("Stopped after maximum tool iterations.")
                return {
                    "answer": "Maximum tool iterations reached",
                    "progress": progress
                }

            # Ask LLM what to do next
            response = llm.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=messages,
                tools=openrouter_tools
            )

            message = response.choices[0].message

            print("\n========================")
            print(f"Iteration {iteration}")
            print("========================")

            print("\nTool Calls:")
            print(message.tool_calls)

            # No tool calls -> final answer
            if not message.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content
                    }
                )

                progress.append("No tool calls were needed; returning final answer.")
                return {
                    "answer": message.content,
                    "progress": progress
                }

            # Execute all tool calls
            executed_calls = set()
            for tool_call in message.tool_calls:

                # Name of the MCP tool the model wants to run.
                tool_name = tool_call.function.name

                # Tool arguments come back as a JSON string, so convert them to a dict.
                arguments = json.loads(
                    tool_call.function.arguments
                )

                call_signature = (
                    tool_name,
                    json.dumps(arguments, sort_keys=True)
                )

                if call_signature in executed_calls:
                    progress.append("Detected repeated tool loop and stopped.")
                    return {
                        "answer": "Agent entered repeated tool loop.",
                        "progress": progress
                    }

                print("\nTool:")
                print(tool_name)

                print("\nArguments:")
                print(arguments)

                try:
                    progress.append(f"Calling tool {tool_name}...")
                    tool_start = time.perf_counter()

                    # Execute MCP Tool
                    tool_result = await client.call_tool(
                        tool_name,
                        arguments
                    )
                    tool_elapsed = round((time.perf_counter() - tool_start) * 1000)
                    progress.append(f"Tool {tool_name} completed in {tool_elapsed}ms.")

                    # Store executed call signature
                    executed_calls.add(call_signature)

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

                    if tool_result.is_error:
                        messages.append(
                            {
                                "role": "user",
                                "content":
                                    f"Tool error:\n{tool_text}"
                            }
                        )
                        progress.append(f"Tool {tool_name} returned an error.")

                        # Persist error state to store
                        conversation_store[session_id] = messages.copy()

                        continue

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

                    # Persist updated conversation to store
                    conversation_store[session_id] = messages.copy()

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
async def main(
        question: str = DEFAULT_QUESTION,
        session_id: str = "local-session"
):

    # This is only for local testing from terminal.
    result = await ask_agent(question, session_id)

    print("\n=== FINAL ANSWER ===\n")
    print(result["answer"])
    print("\n=== PROGRESS ===\n")
    print(result.get("progress", []))


if __name__ == "__main__":
    asyncio.run(main())
