from fastapi import APIRouter, Depends, HTTPException
from app.database.connection import get_connection
from app.services.conversation_service import (
    get_messages,
    delete_conversation,
    get_all_conversations
)
from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)


# ---------- View a session's conversations ----------
@router.get("/{session_id}")
def get_conversation(
    session_id: str,
    user=Depends(get_current_user)
):
    """
    Get the conversation history for a given session ID.
    """
    conn = get_connection()

    try:
        return get_messages(
            session_id,
            user["user_id"],
            conn
        )

    finally:
        conn.close()


# ---------- View all sessions' conversations ----------
@router.get("/")
def get_conversations(
    user=Depends(get_current_user)
):

    conn = get_connection()

    try:
        return get_all_conversations(
            user["user_id"],
            conn
        )

    finally:
        conn.close()

# ---------- Clear a session's conversations ----------
@router.delete("/{session_id}")
def delete_chat(
    session_id: str, 
    user=Depends(get_current_user)
):
    """
    Clear the conversation history for a given session ID.
    """
    conn = get_connection()

    try:

        delete_conversation(
            session_id,
            user["user_id"],
            conn
        )

        return {
            "message": "Conversation deleted"
        }

    finally:
        conn.close()