from fastapi import APIRouter
from app.llm.llm_client import conversation_store


router = APIRouter(
    prefix="/memory",
    tags=["Memory"]
)


# ---------- View a session's memory ----------
@router.get("/{session_id}")
def get_memory(session_id: str):
    """
    Get the conversation history for a given session ID.
    """
    return conversation_store.get(
        session_id,
        []
    )


# ---------- View all sessions' memory ----------
@router.get("/")
def get_all_memory():
    """
    Get the conversation history for all sessions.
    """
    return conversation_store


# ---------- Clear a session's memory ----------
@router.delete("/{session_id}")
def clear_memory(session_id: str):
    """
    Clear the conversation history for a given session ID.
    """
    if session_id in conversation_store:
        del conversation_store[session_id]
        return {"message": f"Memory for session {session_id} cleared."}
    else:
        return {"message": f"No memory found for session {session_id}."}