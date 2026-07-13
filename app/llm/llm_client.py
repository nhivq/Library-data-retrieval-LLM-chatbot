import asyncio
import json
import logging
import time

from app.llm.tool_result_processor import process_tool_result
from app.llm.setup import client
from app.llm.tool_converter import mcp_tool_to_openrouter
from app.services.conversation_service import edit_user_message, initialize_conversation, get_messages, save_message
from app.database.connection import get_connection
from app.llm.prompts import SYSTEM_PROMPT, DEFAULT_QUESTION
from app.llm.openrouter_client import call_llm

logger = logging.getLogger(__name__)

# ---------- Helper Functions ----------
def summarize_tool_result(data):
    """Build a short progress summary for a tool result."""

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
    """Load MCP tools once and convert them to OpenRouter tool schemas."""

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
    user_id: int,
    edited_message_id: int | None = None
):
    """Stream an agent answer as Server-Sent Events.

    The agent loop alternates between model calls and MCP tool execution until
    the model returns final text without tool calls, or the iteration cap is
    reached. Each yielded line follows the SSE "data: ..." format expected by
    the frontend.
    """

    logger.info(
        "agent stream started",
        extra={"event": "agent_stream_start", "session_id": session_id, "user_id": user_id},
    )
    yield 'data: {"type":"progress","message":"Starting"}\n\n'
    async with client:
        progress = []
        step_number = 1
        start = time.perf_counter()
        openrouter_tools = await get_openrouter_tools()
        logger.info(
            "tool schemas loaded",
            extra={
                "event": "tool_schemas_loaded",
                "user_id": user_id,
                "session_id": session_id,
                "tool_count": len(openrouter_tools),
                "latency_ms": round((time.perf_counter() - start) * 1000),
            },
        )
        conn = get_connection()
        try:
            formatted_prompt = SYSTEM_PROMPT.format(user_id=user_id)
            deleted_all_conversations = False
            start = time.perf_counter()
            # Ensure the conversation exists and has the current system prompt
            # before saving this turn's user message.
            initialize_conversation(session_id, formatted_prompt, user_id, conn)
            logger.info(
                "conversation initialized",
                extra={
                    "event": "conversation_init",
                    "session_id": session_id,
                    "user_id": user_id,
                    "latency_ms": round((time.perf_counter() - start) * 1000),
                },
            )
            start = time.perf_counter()
            if edited_message_id is not None:
                edit_user_message(
                    session_id,
                    user_id,
                    edited_message_id,
                    question,
                    conn
                )
                user_message_id = edited_message_id
            else:
                user_message_id = save_message(session_id, "user", question, user_id, conn)
            user_message_payload = json.dumps(
                {
                    "type": "user_message",
                    "id": user_message_id
                }
            )
            yield f"data: {user_message_payload}\n\n"
            logger.info(
                "user message persisted",
                extra={
                    "event": "user_message_persisted",
                    "session_id": session_id,
                    "user_id": user_id,
                    "latency_ms": round((time.perf_counter() - start) * 1000),
                },
            )
            start = time.perf_counter()
            stored_messages = get_messages(session_id, user_id, conn)
            messages = [
                {
                    "role": message["role"],
                    "content": message["content"]
                }
                for message in stored_messages
            ]
            # get_messages hides system messages from the UI. Add the prompt
            # back into the LLM context if it is not already present.
            if not any(m["role"] == "system" for m in messages):
                messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": formatted_prompt
                    }
                )
            logger.info(
                "conversation history loaded",
                extra={
                    "event": "conversation_history_loaded",
                    "session_id": session_id,
                    "user_id": user_id,
                    "message_count": len(messages),
                    "latency_ms": round((time.perf_counter() - start) * 1000),
                },
            )
            # Prevent infinite tool loops if the model keeps requesting tools
            # without producing a final answer.
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
                logger.info(
                    "LLM request started",
                    extra={
                        "event": "llm_request_started",
                        "session_id": session_id,
                        "user_id": user_id,
                        "iteration": iteration,
                    },
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
                        logger.info(
                            "LLM emitted tool calls",
                            extra={
                                "event": "llm_tool_calls",
                                "session_id": session_id,
                                "user_id": user_id,
                                "iteration": iteration,
                            },
                        )
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
                    logger.info(
                        "LLM completed without tool calls",
                        extra={
                            "event": "llm_final_response",
                            "session_id": session_id,
                            "user_id": user_id,
                            "response_chars": len(assistant_text),
                        },
                    )
                    messages.append(
                        {
                            "role": "assistant",
                            "content": assistant_text
                        }
                    )
                    break
                # Parse and execute all accumulated tool calls after the stream
                # finishes. OpenAI-compatible streams split function arguments
                # across chunks, so executing earlier could use partial JSON.
                for idx, tc_data in sorted(tool_calls_accumulator.items()):
                    tool_name = tc_data["name"]
                    arguments = json.loads(tc_data["arguments"])
                    logger.info(
                        "executing tool",
                        extra={
                            "event": "tool_execute",
                            "session_id": session_id,
                            "user_id": user_id,
                            "tool_name": tool_name,
                        },
                    )
                    # Inject authenticated user_id server-side. The model never
                    # gets to choose which user's bookmarks/history to mutate.
                    if tool_name in [
                        "save_bookmarks",
                        "get_bookmarks",
                        "delete_bookmarks",
                        "delete_all_conversations"
                    ]:
                        arguments["user_id"] = user_id
                    try:
                        tool_start = time.perf_counter()
                        # Call the MCP tool via the active FastMCP client.
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
                            # Feed tool errors back into the model context so it
                            # can explain the failure or choose another tool.
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
                            logger.info(
                                "tool result parsed",
                                extra={
                                    "event": "tool_result_parsed",
                                    "session_id": session_id,
                                    "user_id": user_id,
                                    "tool_name": tool_name,
                                    "response_chars": len(tool_text),
                                },
                            )
                        except Exception:
                            logger.warning(
                                "tool result was not JSON",
                                extra={
                                    "event": "tool_result_non_json",
                                    "session_id": session_id,
                                    "user_id": user_id,
                                    "tool_name": tool_name,
                                },
                            )
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
                        if tool_name == "delete_all_conversations":
                            deleted_all_conversations = True
                        step_number += 1
                        # Add the OpenAI-style assistant tool call plus the tool
                        # result so the next model call can reason from it.
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
                        logger.exception(
                            "tool execution failed",
                            extra={
                                "event": "tool_execution_error",
                                "session_id": session_id,
                                "user_id": user_id,
                                "tool_name": tool_name,
                                "error": str(e),
                            },
                        )
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
            # If the user asked to delete all history, do not recreate
            # a new conversation by saving the final confirmation message.
            if not deleted_all_conversations:
                save_message(
                    session_id,
                    "assistant",
                    assistant_text,
                    user_id,
                    conn
                )
        
        except Exception as e:
            logger.exception(
                "agent stream failed",
                extra={
                    "event": "agent_stream_error",
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            raise
        
        finally:
            conn.close()
            logger.info(
                "agent stream ended",
                extra={"event": "agent_stream_end", "session_id": session_id, "user_id": user_id},
            )


# Local Test
async def main(
        question: str = DEFAULT_QUESTION,
        session_id: str = "local-session"
):
    """Manual terminal entry point for checking the agent loop locally."""

    # This is only for local testing from terminal.
    result = await ask_agent_stream(question, session_id, user_id=0)

    logger.info(
        "local test completed",
        extra={"event": "local_test_complete", "answer_length": len(result["answer"])}
    )


if __name__ == "__main__":
    asyncio.run(main())
