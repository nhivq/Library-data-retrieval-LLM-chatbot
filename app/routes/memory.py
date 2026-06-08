from fastapi import APIRouter
from app.llm.llm_client import conversation_store


router = APIRouter(
    prefix="/memory",
    tags=["Memory"]
)

@router.get("/{session_id}")
def get_memory(session_id: str):
    """
    Get the conversation history for a given session ID.
    """
    return conversation_store.get(
        session_id,
        []
    )