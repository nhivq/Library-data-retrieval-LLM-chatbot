from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.database.connection import get_db
from app.main import app
from tests.conftest import FakeConnection, FakeCursor


def test_bookmark_route_uses_dependency_overrides(sample_book):
    cursor = FakeCursor(fetchall_results=[[sample_book]])
    conn = FakeConnection([cursor])

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 7,
        "username": "ada",
        "email": "ada@example.com",
        "role": "user",
    }
    app.dependency_overrides[get_db] = lambda: conn

    try:
        response = TestClient(app).get("/bookmarks/")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [sample_book]
    assert cursor.executed[0][1] == (7,)
