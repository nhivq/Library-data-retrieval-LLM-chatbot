from fastapi import APIRouter

from app.schemas.chat_schema import ChatRequest, ChatResponse

from app.llm.llm_client import ask_agent


router = APIRouter()


@router.post(
        "/chat", response_model=ChatResponse
)
# using async because ask_agent() is already async def ask_agent(...)
async def chat(
    request: ChatRequest
):
    result = await ask_agent(
        request.message,
        request.session_id or "web-session"
    )
    return ChatResponse(
        answer=result["answer"],
        progress=result.get("progress", [])
    )
