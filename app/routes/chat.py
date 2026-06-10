import time

from fastapi import APIRouter

from app.schemas.chat_schema import ChatRequest, ChatResponse

from app.llm.llm_client import ask_agent


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
    start = time.perf_counter()

    result = await ask_agent(
        request.message,
        request.session_id or "web-session",
        request.user_id
    )

    print(
        "TOTAL REQUEST:",
        round((time.perf_counter() - start) * 1000),
        "ms"
    )

    return ChatResponse(
        answer=result["answer"],
        progress=result.get("progress", [])
    )
