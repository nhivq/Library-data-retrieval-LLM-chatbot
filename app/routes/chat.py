from fastapi import APIRouter

from app.schemas.chat_schema import (
    ChatRequest,
    ChatResponse
)

from app.llm.llm_client import ask_agent


router = APIRouter()