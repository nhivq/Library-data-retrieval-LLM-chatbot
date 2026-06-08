from app.services.conversation_service import (
    initialize_conversation,
    save_message,
    get_messages
)
from app.database.connection import get_connection

conn = get_connection()

try:

    session_id = "test-session"

    initialize_conversation(
        session_id,
        "You are a helpful assistant",
        conn
    )

    save_message(
        session_id,
        "user",
        "Hello",
        conn
    )

    print(
        get_messages(
            session_id,
            conn
        )
    )

finally:
    conn.close()