from fastapi import APIRouter
from app.database.connection import get_connection
from app.services.conversation_service import (
    get_messages,
    delete_conversation,
    get_all_conversations
)

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)


# ---------- View a session's conversations ----------
@router.get("/{session_id}")
def get_conversation(session_id: str):
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


# ---------- View all sessions' conversations ----------
@router.get("/")
def get_conversations():

    conn = get_connection()

    try:
        return get_all_conversations(conn)

    finally:
        conn.close()

# ---------- Clear a session's conversations ----------
@router.delete("/{session_id}")
def delete_chat(session_id: str):
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
            "message": "Conversation deleted"
        }

    finally:
        conn.close()