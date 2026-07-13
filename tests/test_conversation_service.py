from app.services import conversation_service
from tests.conftest import FakeConnection, FakeCursor


def test_get_or_create_conversation_returns_existing_id_without_commit():
    cursor = FakeCursor(fetchone_results=[{"id": 42}])
    conn = FakeConnection([cursor])

    result = conversation_service.get_or_create_conversation(
        session_id="session-1",
        user_id=7,
        conn=conn,
    )

    assert result == 42
    assert len(cursor.executed) == 2
    assert cursor.executed[1][1] == ("session-1", 7)
    assert conn.commits == 0
    assert cursor.closed


def test_get_or_create_conversation_inserts_and_commits_when_missing():
    cursor = FakeCursor(fetchone_results=[None, {"id": 99}])
    conn = FakeConnection([cursor])

    result = conversation_service.get_or_create_conversation(
        session_id="session-1",
        user_id=7,
        conn=conn,
    )

    assert result == 99
    assert cursor.executed[2][1] == ("session-1", 7)
    assert conn.commits == 1
    assert cursor.closed


def test_initialize_conversation_saves_system_message_only_when_empty(monkeypatch):
    monkeypatch.setattr(conversation_service, "get_or_create_conversation", lambda *args, **kwargs: 42)
    saved_messages = []
    monkeypatch.setattr(
        conversation_service,
        "save_message",
        lambda session_id, role, content, user_id, conn: saved_messages.append(
            (session_id, role, content, user_id)
        ),
    )
    cursor = FakeCursor(fetchone_results=[None])
    conn = FakeConnection([cursor])

    conversation_service.initialize_conversation(
        session_id="session-1",
        system_prompt="You are helpful",
        user_id=7,
        conn=conn,
    )

    assert saved_messages == [("session-1", "system", "You are helpful", 7)]
    assert cursor.closed


def test_save_message_commits_and_returns_message_id(monkeypatch):
    monkeypatch.setattr(conversation_service, "get_or_create_conversation", lambda *args, **kwargs: 42)
    cursor = FakeCursor(fetchone_results=[{"id": 123}])
    conn = FakeConnection([cursor])

    result = conversation_service.save_message(
        session_id="session-1",
        role="user",
        content="hello",
        user_id=7,
        conn=conn,
    )

    assert result == 123
    assert cursor.executed[0][1] == (42, "user", "hello")
    assert conn.commits == 1
    assert cursor.closed


def test_get_messages_returns_plain_dicts():
    cursor = FakeCursor(fetchall_results=[[{"role": "user", "content": "hello"}]])
    conn = FakeConnection([cursor])

    result = conversation_service.get_messages(
        session_id="session-1",
        user_id=7,
        conn=conn,
    )

    assert result == [{"role": "user", "content": "hello"}]
    assert cursor.executed[0][1] == ("session-1", 7)
    assert cursor.closed
