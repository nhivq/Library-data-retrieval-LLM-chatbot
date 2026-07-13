import pytest

from app.services import bookmark_service
from tests.conftest import FakeConnection, FakeCursor


def test_save_bookmark_commits_insert():
    cursor = FakeCursor()
    conn = FakeConnection([cursor])

    result = bookmark_service.save_bookmark(
        user_id=7,
        work_key="/works/OL1W",
        conn=conn,
    )

    assert result == {"message": "Bookmark saved"}
    assert cursor.executed[0][1] == (7, "/works/OL1W")
    assert conn.commits == 1
    assert cursor.closed


def test_save_bookmark_rolls_back_on_error():
    cursor = FakeCursor(fail_on_execute=True)
    conn = FakeConnection([cursor])

    with pytest.raises(RuntimeError):
        bookmark_service.save_bookmark(
            user_id=7,
            work_key="/works/OL1W",
            conn=conn,
        )

    assert conn.rollbacks == 1
    assert cursor.closed


def test_get_bookmark_returns_rows_for_user():
    rows = [{"work_key": "/works/OL1W", "title": "Dune"}]
    cursor = FakeCursor(fetchall_results=[rows])
    conn = FakeConnection([cursor])

    assert bookmark_service.get_bookmark(user_id=7, conn=conn) == rows
    assert cursor.executed[0][1] == (7,)
    assert cursor.closed


def test_delete_bookmark_scopes_delete_to_user_and_work_key():
    cursor = FakeCursor()
    conn = FakeConnection([cursor])

    result = bookmark_service.delete_bookmark(
        work_key="/works/OL1W",
        user_id=7,
        conn=conn,
    )

    assert result == {"message": "Bookmark deleted"}
    assert cursor.executed[0][1] == (7, "/works/OL1W")
    assert conn.commits == 1
    assert cursor.closed
