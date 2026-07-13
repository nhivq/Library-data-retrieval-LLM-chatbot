import logging
import time
from psycopg2.extras import RealDictCursor

"""
Service helpers for conversation and message persistence.

This module manages conversation ownership by associating
conversations and messages with authenticated users.

All database operations require user_id to ensure users can only
access their own conversations.

Functions receive an active database connection and manage their own
cursor lifecycle. Errors rollback transactions before being propagated.
"""

logger = logging.getLogger(__name__)


def get_or_create_conversation(
        session_id: str,
        user_id: int,
        conn
) -> int:
    """Return an existing conversation id or create a new one for the user."""

    # RealDictCursor lets the code access rows by column name instead of index.
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # Debug visibility for deployment/database mismatch problems.
        cursor.execute("""
        SELECT current_database(), current_schema()
        """)

        logger.debug(
            "database context resolved",
            extra={"event": "db_context", "session_id": session_id, "user_id": user_id},
        )

        # session_id alone is not trusted; user_id is included so users can
        # only reuse conversations they own.
        query_select = """
                       SELECT id 
                       FROM conversations 
                       WHERE session_id = %s
                       AND user_id=%s
                       """

        cursor.execute(query_select, (session_id, user_id))

        result = cursor.fetchone()

        if result:
            return result["id"]

        # No conversation exists for this user/session pair, so create one and
        # return the generated primary key.
        query_insert = """
                       INSERT INTO conversations (session_id, user_id) 
                       VALUES (%s, %s) 
                       RETURNING id
                       """

        start = time.perf_counter()

        cursor.execute(
            query_insert,
            (session_id, user_id)
        )

        logger.info(
            "conversation created",
            extra={
                "event": "conversation_create",
                "session_id": session_id,
                "user_id": user_id,
                "latency_ms": round((time.perf_counter() - start) * 1000),
            },
        )

        new_result = cursor.fetchone()

        start = time.perf_counter()

        # Commit the insert so the new conversation is persisted
        conn.commit()

        logger.info(
            "conversation commit completed",
            extra={
                "event": "conversation_commit",
                "session_id": session_id,
                "user_id": user_id,
                "latency_ms": round((time.perf_counter() - start) * 1000),
            },
        )

        return new_result["id"]

    except Exception:

        conn.rollback()

        raise

    finally:

        cursor.close()


def initialize_conversation(
        session_id: str,
        system_prompt: str,
        user_id: int,
        conn
):
    """
    Initialize a conversation with a system message if it is empty.

    The system prompt is persisted only once per conversation. Later requests
    can rebuild the LLM context from stored messages.
    """

    conversation_id = get_or_create_conversation(
        session_id,
        user_id,
        conn
    )

    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT 1
            FROM messages
            WHERE conversation_id = %s
            LIMIT 1
            """,
            (conversation_id,)
        )

        exists = cursor.fetchone()

        if not exists:

            save_message(
                session_id,
                "system",
                system_prompt,
                user_id,
                conn
            )

    finally:

        cursor.close()


def get_all_conversations(
        user_id: int,
        conn
) -> list:
    """Return all conversations owned by a user with a readable preview."""

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # The first user message becomes the sidebar title.
        # The last non-system message time controls ordering and subtitle.
        query = """
            SELECT c.*,
                   first_user_message.content AS first_message,
                   last_message.created_at AS last_message_at

            FROM conversations c

                     LEFT JOIN LATERAL (
                         SELECT m.content
                         FROM messages m
                         WHERE m.conversation_id = c.id
                           AND m.role = 'user'
                         ORDER BY m.id ASC
                         LIMIT 1
                     ) AS first_user_message
                       ON TRUE

                     LEFT JOIN LATERAL (
                         SELECT m.created_at
                         FROM messages m
                         WHERE m.conversation_id = c.id
                           AND m.role != 'system'
                         ORDER BY m.id DESC
                         LIMIT 1
                     ) AS last_message
                       ON TRUE

            WHERE c.user_id = %s
            ORDER BY COALESCE(last_message.created_at, c.created_at) DESC,
                     c.id DESC;
            """

        cursor.execute(query, (user_id,))

        conversations = cursor.fetchall()

        return [dict(row) for row in conversations]

    finally:

        cursor.close()


def save_message(
        session_id: str,
        role: str,
        content: str,
        user_id: int,
        conn
):
    """Persist one chat message in the user's conversation."""

    start = time.perf_counter()

    conversation_id = get_or_create_conversation(session_id, user_id, conn)

    logger.info(
        "conversation lookup completed",
        extra={
            "event": "conversation_lookup",
            "session_id": session_id,
            "user_id": user_id,
            "latency_ms": round((time.perf_counter() - start) * 1000),
        },
    )

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # Store only the role/content pair expected by OpenAI-style chat APIs.
        query = """
            INSERT INTO messages 
                (conversation_id, role, content) 

            VALUES
                (%s, %s, %s)
            
                RETURNING id
            """

        cursor.execute(query, (conversation_id, role, content))

        message = cursor.fetchone()

        # Commit so the message is durable
        conn.commit()

        return message["id"]

    except Exception:

        conn.rollback()

        raise

    finally:

        cursor.close()


def get_messages(
        session_id: str,
        user_id: int,
        conn
) -> list:
    """Load non-system messages for a user/session in chronological order."""

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # Hide persisted system messages from the frontend chat history.
        # llm_client inserts the system message into the model context when
        # needed, so the user-facing history stays clean.
        query = """
            SELECT m.role, 
                m.content

            FROM messages m

                JOIN conversations c
                    ON m.conversation_id = c.id

            WHERE c.session_id = %s
            AND c.user_id=%s
            AND role!='system'

            ORDER BY m.id ASC
            """

        cursor.execute(query, (session_id, user_id))

        messages = cursor.fetchall()

        return [dict(row) for row in messages]

    finally:

        cursor.close()


def delete_conversation(
        session_id: str,
        user_id: int,
        conn
):
    """Delete one conversation owned by the user."""

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # Messages are removed by the ON DELETE CASCADE relationship.
        query = """
            DELETE 
            FROM conversations 
            WHERE session_id = %s
            AND user_id=%s
            """

        cursor.execute(query, (session_id, user_id))

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        cursor.close()


def delete_all_conversations(
        user_id: int,
        conn
):
    """Delete every conversation owned by one user and return the count."""

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # Delete only conversations owned by this user.
        # Messages are removed by the ON DELETE CASCADE rule.
        query = """
            DELETE
            FROM conversations
            WHERE user_id = %s
            """

        cursor.execute(query, (user_id,))

        deleted_count = cursor.rowcount

        conn.commit()

        return deleted_count

    except Exception:

        conn.rollback()

        raise

    finally:

        cursor.close()
