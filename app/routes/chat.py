from fastapi import APIRouter, StreamingResponse
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.llm.llm_client import ask_agent_stream


router = APIRouter(
    tags=["Chat"]
)


@router.post(
        "/chat", response_model=ChatResponse
)
# using async because ask_agent() is already async def ask_agent(...)
async def chat(
    request: ChatRequest
):

    return StreamingResponse(
        ask_agent_stream(
            request.message,
            request.session_id
            or
            "web-session",
            request.user_id
        ),
        media_type="text/event-stream"
    )

