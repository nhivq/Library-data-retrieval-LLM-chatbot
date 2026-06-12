from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.chat_schema import ChatRequest
from app.llm.llm_client import ask_agent_stream


router = APIRouter(
    tags=["Chat"]
)


@router.post("/chat")
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