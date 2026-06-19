import asyncio
import json
import time

from dns import message
from app.llm.tool_result_processor import process_tool_result
from app.llm.setup import client
from app.llm.tool_converter import mcp_tool_to_openrouter
from app.services.conversation_service import initialize_conversation, get_messages, save_message
from app.database.connection import get_connection
from app.llm.prompts import SYSTEM_PROMPT, DEFAULT_QUESTION
from app.llm.openrouter_client import call_llm

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


# ---------- Agent ----------
async def ask_agent_stream(
    question: str,
    session_id: str,
    user_id: int
):
    print("\n===== Stream START")
    yield 'data: {"type":"progress","message":"Starting"}\n\n'
    async with client:
        progress = []
        step_number = 1
        start = time.perf_counter()
        openrouter_tools = await get_openrouter_tools()
        print(
            "stream list_tools:",
            round((time.perf_counter() - start) * 1000),
            "ms",
            "tools:",
            len(openrouter_tools)
        )
        conn = get_connection()
        try:
            formatted_prompt = SYSTEM_PROMPT.format(user_id=user_id)
            start = time.perf_counter()
            initialize_conversation(session_id, formatted_prompt, user_id, conn)
            print(
                "stream initialize_conversation:",
                round((time.perf_counter() - start) * 1000),
                "ms"
            )
            start = time.perf_counter()
            save_message(session_id, "user", question, user_id, conn)
            print(
                "stream save_message user:",
                round((time.perf_counter() - start) * 1000),
                "ms"
            )
            start = time.perf_counter()
            messages = get_messages(session_id, user_id, conn)
            if not any(m["role"] == "system" for m in messages):
                messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": formatted_prompt
                    }
                )
            print(
                "stream get_messages:",
                round((time.perf_counter() - start) * 1000),
                "ms",
                "message count:",
                len(messages),
                "chars:",
                len(json.dumps(messages))
            )
            MAX_ITERATIONS = 10
            iteration = 0
            assistant_text = ""
            while True:
                iteration += 1
                if iteration > MAX_ITERATIONS:
                    break
                response = call_llm(
                    messages=messages,
                    tools=openrouter_tools,
                    stream=True
                )
                # Initialize an accumulator to assemble stream chunks of tool calls.
                # This is necessary because arguments and names are received piece-by-piece.
                tool_calls_accumulator = {}
                assistant_text = ""
                for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    # ----------------------------
                    # CASE 1: normal text response
                    # ----------------------------
                    if delta.content:
                        assistant_text += delta.content
                        payload = json.dumps(
                            {
                                "type": "delta",
                                "delta": delta.content
                            }
                        )
                        yield f"data: {payload}\n\n"
                    # ----------------------------
                    # CASE 2: tool call response
                    # ----------------------------
                    if delta.tool_calls:
                        # Emit progress to let the frontend know a tool execution has started.
                        yield 'data: {"type":"progress","message":"Using tool"}\n\n'
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_accumulator:
                                tool_calls_accumulator[idx] = {
                                    "id": tc.id if tc.id else "",
                                    "name": (
                                        tc.function.name
                                        if tc.function and tc.function.name
                                        else ""
                                    ),
                                    "arguments": ""
                                }
                            else:
                                if tc.id:
                                    tool_calls_accumulator[idx]["id"] = tc.id
                                if tc.function.name:
                                    tool_calls_accumulator[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_accumulator[idx]["arguments"] += tc.function.arguments
                # If no tool calls were requested during the stream, this is the final assistant response.
                # We append it to the in-memory context and break out of the ReAct loop.
                if not tool_calls_accumulator:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": assistant_text
                        }
                    )
                    break
                # Parse and execute all accumulated tool calls.
                for idx, tc_data in sorted(tool_calls_accumulator.items()):
                    tool_name = tc_data["name"]
                    arguments = json.loads(tc_data["arguments"])
                # Inject authenticated user_id only for bookmark operations
                if tool_name in [
                    "save_bookmarks",
                    "get_bookmarks",
                    "delete_bookmarks"
                ]:
                    arguments["user_id"] = user_id
                    try:
                        tool_start = time.perf_counter()
                        # Call the MCP tool via the active fastmcp client.
                        tool_result = await client.call_tool(
                            tool_name,
                            arguments
                        )
                        tool_elapsed = round((time.perf_counter() - tool_start) * 1000)
                        if not tool_result.content:
                            tool_text = f"Tool {tool_name} returned no content."
                        else:
                            tool_text = tool_result.content[0].text
                        if tool_result.is_error:
                            messages.append(
                                {
                                    "role": "user",
                                    "content": f"Tool error:\n{tool_text}"
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
                        tool_data = None
                        try:
                            # Compact the tool payloads to avoid hitting context window limits.
                            tool_data, compact_text = process_tool_result(
                                tool_name,
                                tool_text
                            )
                            print("Tool output chars:", len(tool_text))
                            print("\nParsed Tool Data:")
                            print(type(tool_data))
                            print(tool_data)
                        except Exception:
                            print("\nTool result is not JSON.")
                            compact_text = tool_text
                        progress.append(
                            {
                                "step": step_number,
                                "tool": tool_name,
                                "arguments": arguments,
                                "summary": summarize_tool_result(tool_data),
                                "duration_ms": tool_elapsed,
                                "status": "completed"
                            }
                        )
                        step_number += 1
                        # Append assistant tool call reference and tool response to history.
                        messages.append(
                            {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": tc_data["id"] or f"call_{idx}",
                                        "type": "function",
                                        "function": {
                                            "name": tool_name,
                                            "arguments": json.dumps(arguments)
                                        }
                                    }
                                ]
                            }
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc_data["id"] or f"call_{idx}",
                                "content": compact_text
                            }
                        )
                    except Exception as e:
                        print("\nTool Error:")
                        print(e)
                        messages.append(
                            {
                                "role": "user",
                                "content": f"Tool {tool_name} failed with error:\n{str(e)}"
                            }
                        )
            payload = json.dumps(
                {
                    "type": "complete",
                    "progress": progress
                }
            )
            yield f"data: {payload}\n\n"
            # Save the final answer to the database after yielding complete,
            # so the user sees the output immediately without waiting for database writes.
            save_message(
                session_id,
                "assistant",
                assistant_text,
                user_id,
                conn
            )
        finally:
            conn.close()
            print("===== ask_agent_stream END =====\n")


# Local Test
async def main(
        question: str = DEFAULT_QUESTION,
        session_id: str = "local-session"
):

    # This is only for local testing from terminal.
    result = await ask_agent_stream(question, session_id, user_id=0)

    print("\n=== FINAL ANSWER ===\n")
    print(result["answer"])
    print("\n=== PROGRESS ===\n")
    print(result.get("progress", []))


if __name__ == "__main__":
    asyncio.run(main())
