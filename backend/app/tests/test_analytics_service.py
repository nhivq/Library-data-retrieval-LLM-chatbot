from backend.app.services import analytics_service


def test_get_dashboard_analytics_returns_cached_payload(monkeypatch):
    cached_payload = {
        "totals": {"books": 1},
        "data_quality": {},
        "top_authors": [],
        "top_tags": [],
        "recent_books": [],
    }

    monkeypatch.setattr(
        analytics_service,
        "get_json",
        lambda key: cached_payload
    )

    class ExplodingConnection:
        def cursor(self, *args, **kwargs):
            raise AssertionError("database should not be queried on cache hit")

    assert analytics_service.get_dashboard_analytics(
        conn=ExplodingConnection()
    ) == cached_payload


def test_get_dashboard_analytics_writes_cache(monkeypatch):
    writes = []

    monkeypatch.setattr(
        analytics_service,
        "get_json",
        lambda key: None
    )
    monkeypatch.setattr(
        analytics_service,
        "set_json",
        lambda key, value, ttl_seconds: writes.append((key, value, ttl_seconds))
    )

    monkeypatch.setattr(
        analytics_service,
        "_count_table",
        lambda cursor, table_name: 0
    )
    monkeypatch.setattr(
        analytics_service,
        "_get_data_quality",
        lambda cursor: {}
    )
    monkeypatch.setattr(
        analytics_service,
        "_get_top_authors",
        lambda cursor: []
    )
    monkeypatch.setattr(
        analytics_service,
        "_get_top_tags",
        lambda cursor: []
    )
    monkeypatch.setattr(
        analytics_service,
        "_get_recent_books",
        lambda cursor: []
    )

    class FakeCursor:
        def close(self):
            pass

    class FakeConnection:
        def cursor(self, *args, **kwargs):
            return FakeCursor()

    payload = analytics_service.get_dashboard_analytics(
        conn=FakeConnection()
    )

    assert payload["totals"]["books"] == 0
    assert writes == [
        (
            analytics_service.ADMIN_ANALYTICS_CACHE_KEY,
            payload,
            analytics_service.ADMIN_ANALYTICS_CACHE_TTL_SECONDS,
        )
    ]
