import pytest

from app.services import auth_service
from tests.conftest import FakeConnection, FakeCursor


def test_register_user_hashes_password_and_commits(monkeypatch):
    cursor = FakeCursor()
    conn = FakeConnection([cursor])
    # Replace bcrypt with a predictable value so this test focuses on service
    # behavior: storing a hash, not the plain password.
    monkeypatch.setattr(auth_service, "hash_password", lambda password: f"hashed:{password}")

    result = auth_service.register_user(
        username="ada",
        email="ada@example.com",
        password="plain-secret",
        conn=conn,
    )

    assert result == {"message": "User registered"}
    assert cursor.executed[0][1] == ("ada", "ada@example.com", "hashed:plain-secret", "user")
    assert conn.commits == 1
    assert conn.rollbacks == 0
    assert cursor.closed


def test_register_user_rolls_back_on_database_error(monkeypatch):
    cursor = FakeCursor(fail_on_execute=True)
    conn = FakeConnection([cursor])
    monkeypatch.setattr(auth_service, "hash_password", lambda password: "hashed")

    with pytest.raises(RuntimeError):
        auth_service.register_user("ada", "ada@example.com", "secret", conn=conn)

    assert conn.commits == 0
    assert conn.rollbacks == 1
    assert cursor.closed


def test_login_user_returns_access_and_refresh_tokens(monkeypatch):
    cursor = FakeCursor(
        fetchone_results=[
            {"user_id": 7, "username": "ada", "password": "stored-hash"}
        ]
    )
    conn = FakeConnection([cursor])
    # Token creation and password checking have their own responsibilities.
    # Here they are mocked so we can verify the login flow around them.
    monkeypatch.setattr(auth_service, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(auth_service, "create_access_token", lambda data: f"access:{data['sub']}")
    monkeypatch.setattr(auth_service, "create_refresh_token", lambda data: f"refresh:{data['sub']}")

    result = auth_service.login_user("ada", "secret", conn=conn)

    assert result == {
        "access_token": "access:7",
        "refresh_token": "refresh:7",
        "token_type": "bearer",
    }
    assert cursor.executed[0][1] == ("ada",)
    assert cursor.closed


def test_login_user_rejects_wrong_password(monkeypatch):
    cursor = FakeCursor(
        fetchone_results=[
            {"user_id": 7, "username": "ada", "password": "stored-hash"}
        ]
    )
    conn = FakeConnection([cursor])
    monkeypatch.setattr(auth_service, "verify_password", lambda plain, hashed: False)

    with pytest.raises(ValueError, match="Wrong password"):
        auth_service.login_user("ada", "bad-secret", conn=conn)

    assert cursor.closed
