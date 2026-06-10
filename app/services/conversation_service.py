import time

from psycopg2.extras import RealDictCursor

"""Service helpers for conversation and message persistence.

This module provides small helper functions that interact with the
`conversations` and `messages` tables. Each function receives an active
database connection object and manages its own cursor lifecycle. Errors
are propagated after rolling back the transaction so callers can handle
them appropriately.
"""

def get_or_create_conversation(
        session_id: str,
        conn
) -> int:
    # Create a cursor that returns dict-like rows for easier field access
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # Try to find an existing conversation for this session_id
        query_select = """
                       SELECT id 
                       FROM conversations 
                       WHERE session_id = %s
                       """

        cursor.execute(query_select, (session_id,))

        result = cursor.fetchone()

        # If a conversation exists, return its id immediately
        if result:
            return result["id"]

        # Otherwise insert a new conversation row and return the new id
        query_insert = """
                       INSERT INTO conversations (session_id) 
                       VALUES (%s) 
                       RETURNING id
                       """

        start = time.perf_counter()

        cursor.execute(
            query_insert,
            (session_id,)
        )

        print(
            "conversation select:",
            round((time.perf_counter() - start) * 1000),
            "ms"
        )

        new_result = cursor.fetchone()

        start = time.perf_counter()

        # Commit the insert so the new conversation is persisted
        conn.commit()

        print(
            "conversation commit:",
            round((time.perf_counter() - start) * 1000),
            "ms"
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
        conn
):
    """
    Initialize a conversation with a system message if it's empty.

    When a new conversation is created, this ensures a system message is
    inserted to prime the conversation context.
    """

    conversation_id = get_or_create_conversation(
        session_id,
        conn
    )

    cursor = conn.cursor()

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
            conn
        )


def get_all_conversations(
        conn
) -> list:
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query = """
            SELECT *
            FROM conversations
            ORDER BY id;
            """

        cursor.execute(query)

        conversations = cursor.fetchall()

        return [dict(row) for row in conversations]

    finally:

        cursor.close()


def save_message(
        session_id: str,
        role: str,
        content: str,
        conn
):
    start = time.perf_counter()

    conversation_id = get_or_create_conversation(session_id, conn)

    print(
    "get_or_create_conversation:",
    round((time.perf_counter()-start)*1000),
    "ms"
    )

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # Insert a new message tied to the conversation id
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
        conn
) -> list:
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # Fetch all messages for the given session in chronological order
        query = """
            SELECT m.role, 
                m.content

            FROM messages m

                JOIN conversations c
                    ON m.conversation_id = c.id

            WHERE c.session_id = %s

            ORDER BY m.id ASC
            """

        cursor.execute(query, (session_id,))

        messages = cursor.fetchall()

        # Return a list of dict-like rows: [{'role':..., 'content':...}, ...]
        return [dict(row) for row in messages]

    finally:

        cursor.close()


def delete_conversation(
        session_id: str,
        conn
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # Remove the conversation (and relying on DB cascade to remove messages if configured)
        query = """
            DELETE 
            FROM conversations 
            WHERE session_id = %s
            """

        cursor.execute(query, (session_id,))

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        cursor.close()

