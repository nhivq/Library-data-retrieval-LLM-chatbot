from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from backend.app.schemas.chat_schema import ChatRequest
from backend.app.llm.llm_client import ask_agent_stream
from backend.app.core.dependencies import get_current_user


router = APIRouter(
    tags=["Chat"]
)


@router.post("/chat")
async def chat(
    request: ChatRequest,
    user=Depends(get_current_user)
):
    """Stream the assistant response for one authenticated chat message."""

    return StreamingResponse(
        ask_agent_stream(
            request.message,
            request.session_id
            or
            "web-session",
            user["user_id"],
            request.edited_message_id
        ),
        media_type="text/event-stream"
    )
