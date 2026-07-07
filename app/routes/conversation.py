from fastapi import APIRouter, Depends, HTTPException
from app.database.connection import get_connection
from app.services.conversation_service import (
    get_messages,
    delete_conversation,
    delete_all_conversations,
    get_all_conversations
)
from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)


@router.get("/{session_id}")
def get_conversation(
    session_id: str,
    user=Depends(get_current_user)
):
    """
    Get the conversation history for a given session ID.
    """
    # This route uses a manual connection because these service helpers are
    # also called from the LLM/MCP flow outside normal FastAPI dependency use.
    conn = get_connection()

    try:
        return get_messages(
            session_id,
            user["user_id"],
            conn
        )

    finally:
        conn.close()


@router.get("/")
def get_conversations(
    user=Depends(get_current_user)
):
    """Return the current user's conversation sessions."""

    conn = get_connection()

    try:
        return get_all_conversations(
            user["user_id"],
            conn
        )

    finally:
        conn.close()


@router.delete("/")
def delete_conversations(
    user=Depends(get_current_user)
):
    """Delete every conversation owned by the authenticated user."""

    conn = get_connection()

    try:

        deleted_count = delete_all_conversations(
            user["user_id"],
            conn
        )

        return {
            "message": "Conversations deleted",
            "deleted_count": deleted_count
        }

    finally:
        conn.close()


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
