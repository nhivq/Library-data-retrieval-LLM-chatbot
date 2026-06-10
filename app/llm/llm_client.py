import asyncio
import json
import os
import time
import requests


"""Client that orchestrates LLM usage, tools, and conversation memory.

This module is responsible for assembling tools from the MCP client,
feeding them to the LLM, executing any requested tool calls, and
maintaining a lightweight conversation store for interactive sessions.
The main entrypoint for the agent loop is `ask_agent` which implements
the ReAct-style loop: ask LLM -> run tools -> send tool outputs back -> repeat.
"""

from app.llm.setup import client, llm
from app.llm.tool_converter import mcp_tool_to_openrouter
from app.services.conversation_service import (
    initialize_conversation,
    get_messages,
    save_message
)
from app.database.connection import get_connection


# ---------- Helper Functions ----------
def summarize_tool_result(data):

    if isinstance(data, list):

        if len(data) == 0:
            return "No results found"

        first = data[0]

        if "author_name" in first:
            return (
                f"Found {len(data)} author(s)"
            )

        if "title" in first:
            return (
                f"Found {len(data)} book(s)"
            )

        return (
            f"Found {len(data)} result(s)"
        )

    if isinstance(data, dict):

        if "title" in data:
            return (
                f"Retrieved book: "
                f"{data['title']}"
            )

        if "author_name" in data:
            return (
                f"Retrieved author: "
                f"{data['author_name']}"
            )

    return "Tool executed successfully"

openrouter_tools_cache = None


async def get_openrouter_tools():
    global openrouter_tools_cache
    if openrouter_tools_cache is None:
        mcp_tools = await client.list_tools()
        openrouter_tools_cache = [
            mcp_tool_to_openrouter(tool)
            for tool in mcp_tools
        ]
    return openrouter_tools_cache


# ---------- Local Testing ----------
DEFAULT_QUESTION = (
    "Delete all bookmarks of user 4. Then, save bookmark /works/OL10000112W "
    "for user 4 and then show all user 4's bookmarks"
)


SYSTEM_PROMPT = (
    "You are a helpful book assistant with access to the app's real book data. "
    "For any question about books, authors, ratings, tags, publication dates, bookmarks, or search results, use the available tools instead of answering from your own knowledge. "
    "If you cannot find an answer in the tool output, say that the data is unavailable rather than inventing book titles, authors, ratings, or dates. "
    "Do not hallucinate or fabricate books."
    "The authenticated user has user_id={user_id}. Never ask for a user_id. Use this user_id whenever bookmark tools require one."
)


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
    
    mcp_start = time.perf_counter()

    async with client:

        print(
            "mcp_startup:",
            round((time.perf_counter()-mcp_start)*1000),
            "ms"
        )

        start = time.perf_counter()

        print(
            "OpenRouter ping:",
            round(
                (time.perf_counter() - start)
                * 1000
            ),
            "ms"
        )

        # Safety protection to avoid infinite tool loops
        MAX_ITERATIONS = 10
        iteration = 0
        progress = []
        step_number = 1

        # Discover available MCP tools and convert them to the format
        # expected by the local LLM client (OpenRouter-like format).
        start = time.perf_counter()
        openrouter_tools = await get_openrouter_tools()
        print(
            "list_tools:",
            round((time.perf_counter() - start) * 1000),
            "ms",
            "tools:",
            len(openrouter_tools)
        )

        # Conversation History - Load existing conversation from the
        # in-memory store or initialize a new one with a system prompt
        print("\n=== SESSION ID ===")
        print(session_id)

        conn = get_connection()

        try:

            start = time.perf_counter()
            initialize_conversation(
                session_id,
                SYSTEM_PROMPT,
                conn
            )
            print(
                "initialize_conversation:",
                round((time.perf_counter() - start) * 1000),
                "ms"
            )

            # Load persisted messages from the DB-backed store and append the
            # current user question, then persist the user message.
            start = time.perf_counter()
            save_message(
                session_id,
                "user",
                question,
                conn
            )
            print(
                "save_message (user):",
                round((time.perf_counter() - start) * 1000),
                "ms"
            )

            start = time.perf_counter()
            messages = get_messages(
                session_id,
                conn
            )
            print(
                "load_messages:",
                round((time.perf_counter() - start) * 1000),
                "ms",
                "message count:",
                len(messages)
            )
            print(
                "Approx prompt chars:",
                len(json.dumps(messages))
            )

            # ReAct Loop: ask the LLM for the next action, run tools if requested
            # and feed results back until a final answer (no tool calls) is produced
            while True:

                iteration += 1

                if iteration > MAX_ITERATIONS:
                    return {
                        "answer": "Maximum tool iterations reached",
                        "progress": progress
                    }

                # Ask LLM what to do next (it may request tools)
                print("MODEL:", "openai/gpt-4o-mini")
                start = time.perf_counter()
                print("Sending request to OpenRouter...")
                response = llm.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=messages,
                    tools=openrouter_tools
                )
                print("Received response from OpenRouter")
                print(
                    "llm_call:",
                    round((time.perf_counter() - start) * 1000),
                    "ms"
                )

                message = response.choices[0].message
                print("\n=== MESSAGE ===")
                print(message)

                print("\n========================")
                print(f"Iteration {iteration}")
                print("========================")

                print("\nTool Calls:")
                print(message.tool_calls)

                # If the LLM returned no tool calls, it's the final assistant answer
                if not message.tool_calls:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": message.content
                        }
                    )

                    save_message(
                        session_id,
                        "assistant",
                        message.content,
                        conn
                    )
                    
                    print(
                        "save_message (assistant):",
                        round((time.perf_counter() - time.perf_counter()) * 1000),
                        "ms"
                    )
                    
                    return {
                        "answer": message.content,
                        "progress": progress
                    }

                # Execute all tool calls that the model requested this turn.
                # Track executed call signatures to detect repeated loops.
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

                    # If we've already executed the exact same call signature,
                    # the agent is stuck in a loop and we should stop.
                    if call_signature in executed_calls:
                        return {
                            "answer": "Agent entered repeated tool loop.",
                            "progress": progress
                        }

                    print("\nTool:")
                    print(tool_name)

                    print("\nArguments:")
                    print(arguments)

                    try:
                        tool_start = time.perf_counter()

                        # Execute MCP Tool via the client
                        tool_result = await client.call_tool(
                            tool_name,
                            arguments
                        )
                        tool_elapsed = round((time.perf_counter() - tool_start) * 1000)

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

                        # If the tool reported an error, append an explanatory
                        # user message to the conversation so the LLM can react.
                        if tool_result.is_error:
                            messages.append(
                                {
                                    "role": "user",
                                    "content":
                                        f"Tool error:\n{tool_text}"
                                }
                            )
                            progress.append(
                                {
                                    "step": step_number,
                                    "tool": tool_name,
                                    "arguments": arguments,
                                    "summary": tool_text,
                                    "duration_ms": tool_elapsed,
                                    "status": "error"
                                }
                            )

                            step_number += 1

                            continue

                        # Debugging: attempt to parse JSON tool output for inspection
                        tool_data = None

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

                        progress.append(
                            {
                                "step": step_number,
                                "tool": tool_name,
                                "arguments": arguments,
                                "summary": summarize_tool_result(
                                    tool_data
                                ),
                                "duration_ms": tool_elapsed,
                                "status": "completed"
                            }
                        )

                        step_number += 1

                        # Feed tool result back to LLM as both assistant and user
                        # messages so the model can incorporate the result in the next step.

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
                                "content": (
                                    f"Tool returned:\n"
                                    f"{tool_text}"
                                )
                            }
                        )

                    except Exception as e:
                        # In case of an exception while executing a tool, append
                        # the error so the LLM can handle the failure path.
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
        
        finally:

            conn.close()


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
