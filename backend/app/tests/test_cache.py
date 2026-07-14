from datetime import date, datetime
from decimal import Decimal

from backend.app.core import cache


class FakeRedis:
    """Tiny Redis replacement that can return values or simulate outages."""

    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error
        self.setex_calls = []

    def get(self, key):
        if self.error:
            raise self.error

        return self.value

    def setex(self, key, ttl_seconds, value):
        if self.error:
            raise self.error

        self.setex_calls.append((key, ttl_seconds, value))


def test_make_cache_key_is_stable_for_dict_order():
    # Stable keys mean the same search filters hit the same cache entry even if
    # Python receives the dictionary fields in a different order.
    assert cache.make_cache_key("books", {"q": "dune", "limit": 10}) == cache.make_cache_key(
        "books",
        {"limit": 10, "q": "dune"},
    )


def test_get_json_returns_none_when_cache_disabled(monkeypatch):
    monkeypatch.setattr(cache, "get_redis_client", lambda: None)

    assert cache.get_json("missing") is None


def test_get_json_returns_parsed_value(monkeypatch):
    monkeypatch.setattr(cache, "get_redis_client", lambda: FakeRedis(value='{"ok": true}'))

    assert cache.get_json("key") == {"ok": True}


def test_get_json_ignores_redis_and_decode_errors(monkeypatch):
    # Cache should never take the API down. If Redis is unavailable or contains
    # bad data, callers should simply behave as if the cache missed.
    monkeypatch.setattr(cache, "get_redis_client", lambda: FakeRedis(error=RuntimeError("down")))
    assert cache.get_json("key") is None

    monkeypatch.setattr(cache, "get_redis_client", lambda: FakeRedis(value="{not json"))
    assert cache.get_json("key") is None


def test_set_json_serializes_common_database_values(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(cache, "get_redis_client", lambda: client)

    cache.set_json(
        "key",
        {
            "day": date(2026, 7, 13),
            "created_at": datetime(2026, 7, 13, 9, 30),
            "rating": Decimal("4.5"),
        },
        ttl_seconds=60,
    )

    # Database rows often contain dates, datetimes, and Decimals. This confirms
    # they become normal JSON values before going into Redis.
    assert client.setex_calls == [
        (
            "key",
            60,
            '{"day": "2026-07-13", "created_at": "2026-07-13T09:30:00", "rating": 4.5}',
        )
    ]
