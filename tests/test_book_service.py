from app.services import book_service
from tests.conftest import FakeConnection, FakeCursor


def test_extract_recommendation_terms_removes_stop_words_and_duplicates():
    assert book_service.extract_recommendation_terms(
        "I want books with dragons and dragons in space"
    ) == ["dragons", "in", "space"]


def test_build_recommendation_groups_skips_empty_groups():
    assert book_service.build_recommendation_groups(
        "give me books",
        concept_groups=["cozy mystery", "the and a"],
    ) == [
        {"group_id": 1, "terms": ["cozy", "mystery"]},
    ]


def test_build_book_embedding_text_joins_available_metadata():
    text = book_service.build_book_embedding_text(
        {
            "title": "Dune",
            "description": "Desert politics",
            "authors": ["Frank Herbert"],
            "tags": ["science fiction", "classic"],
            "languages": ["English"],
            "publishers": [],
        }
    )

    assert text == "Dune\nDesert politics\nFrank Herbert\nscience fiction, classic\nEnglish"


def test_get_books_returns_cached_value_without_database(monkeypatch, sample_book):
    monkeypatch.setattr(book_service, "get_json", lambda key: [sample_book])

    assert book_service.get_books(limit=10, conn=None) == [sample_book]


def test_get_books_clamps_limit_and_writes_cache(monkeypatch, sample_book):
    cursor = FakeCursor(fetchall_results=[[sample_book]])
    conn = FakeConnection([cursor])
    writes = []
    monkeypatch.setattr(book_service, "get_json", lambda key: None)
    monkeypatch.setattr(
        book_service,
        "set_json",
        lambda key, value, ttl_seconds: writes.append((key, value, ttl_seconds)),
    )

    result = book_service.get_books(limit=500, conn=conn)

    assert result == [sample_book]
    assert cursor.executed[0][1] == (100,)
    assert writes[0][1] == [sample_book]
    assert writes[0][2] == book_service.BOOK_LIST_CACHE_TTL_SECONDS
    assert cursor.closed


def test_search_books_builds_expected_filters_and_pagination(monkeypatch, sample_book):
    cursor = FakeCursor(fetchall_results=[[sample_book]])
    conn = FakeConnection([cursor])
    monkeypatch.setattr(book_service, "get_json", lambda key: None)
    monkeypatch.setattr(book_service, "set_json", lambda key, value, ttl_seconds: None)

    result = book_service.search_books(
        q="Dune",
        author="Herbert",
        min_rating=4.0,
        tag="science",
        published_after_year=1960,
        page=2,
        limit=5,
        conn=conn,
    )

    query, params = cursor.executed[0]
    assert result == [sample_book]
    assert "b.title ~* %s" in query
    assert "filter_a.author_name ILIKE %s" in query
    assert params == [r"\mDune\M", "%Herbert%", 4.0, "%science%", 1960, 5, 5]


def test_recommend_books_uses_prepared_concepts_and_clamped_limit(monkeypatch, sample_book):
    cursor = FakeCursor(fetchall_results=[[sample_book]])
    conn = FakeConnection([cursor])
    monkeypatch.setattr(book_service, "get_json", lambda key: None)
    monkeypatch.setattr(book_service, "set_json", lambda key, value, ttl_seconds: None)

    result = book_service.recommend_books(
        prompt="space politics",
        concept_groups=["space politics", "desert survival"],
        limit=99,
        conn=conn,
    )

    assert result == [sample_book]
    prepared_groups, concept_count, limit = cursor.executed[0][1]
    assert prepared_groups.adapted == [
        {"group_id": 1, "terms": ["space", "politics"]},
        {"group_id": 2, "terms": ["desert", "survival"]},
    ]
    assert concept_count == 2
    assert limit == 20


def test_semantic_search_formats_embedding_and_clamps_limit(monkeypatch, sample_book):
    cursor = FakeCursor(fetchall_results=[[sample_book]])
    conn = FakeConnection([cursor])
    monkeypatch.setattr(book_service, "get_json", lambda key: None)
    monkeypatch.setattr(book_service, "set_json", lambda key, value, ttl_seconds: None)
    monkeypatch.setattr(book_service, "embed_text", lambda query: [0.1, 0.2])
    monkeypatch.setattr(book_service, "format_vector", lambda embedding: "[0.1,0.2]")

    result = book_service.semantic_search_books("desert planets", limit=99, conn=conn)

    assert result == [sample_book]
    assert cursor.executed[0][1] == ("[0.1,0.2]", "[0.1,0.2]", 20)
