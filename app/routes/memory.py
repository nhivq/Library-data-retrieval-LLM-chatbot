from fastapi import APIRouter
from app.database.connection import get_connection
from app.services.conversation_service import (
    get_messages,
    delete_conversation,
    get_all_conversations
)

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
    conn = get_connection()

    try:
        return get_messages(
            session_id,
            conn
        )

    finally:
        conn.close()


# ---------- View all sessions' memory ----------
@router.get("/")
def get_all_memory():

    conn = get_connection()

    try:
        return get_all_conversations(conn)

    finally:
        conn.close()

# ---------- Clear a session's memory ----------
@router.delete("/{session_id}")
def clear_memory(session_id: str):
    """
    Clear the conversation history for a given session ID.
    """
    conn = get_connection()

    try:

        delete_conversation(
            session_id,
            conn
        )

        return {
            "message":
                f"Memory for session {session_id} cleared."
        }

    finally:
        conn.close()