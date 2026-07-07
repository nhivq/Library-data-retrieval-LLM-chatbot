from datetime import date
from pydantic import BaseModel


class BookResponse(BaseModel):
    """Base book shape returned by normal list/detail endpoints."""

    work_key: str
    title: str
    tags: list[str] | None = None
    publish_date: date | None = None
    rating: float | None = None
    cover_id: int | None = None
    authors: list[str] = []


class SimilarBookResponse(BaseModel):
    """Book response plus metadata similarity score."""

    work_key: str
    title: str
    tags: list[str] | None = None
    publish_date: date | None = None
    rating: float | None = None
    cover_id: int | None = None
    authors: list[str] = []
    similarity_score: float


class RecommendationBookResponse(BaseModel):
    """Book response plus recommendation group scoring fields."""

    work_key: str
    title: str
    tags: list[str] | None = None
    publish_date: date | None = None
    rating: float | None = None
    cover_id: int | None = None
    authors: list[str] = []
    matched_concept_count: int
    concept_count: int
    recommendation_score: float


class SemanticBookResponse(BaseModel):
    """Book response plus pgvector semantic similarity score."""

    work_key: str
    title: str
    tags: list[str] | None = None
    publish_date: date | None = None
    rating: float | None = None
    cover_id: int | None = None
    authors: list[str] = []
    semantic_score: float


class HybridBookResponse(BaseModel):
    """Book response plus keyword, semantic, and combined ranking scores."""

    work_key: str
    title: str
    tags: list[str] | None = None
    publish_date: date | None = None
    rating: float | None = None
    cover_id: int | None = None
    authors: list[str] = []
    keyword_score: float
    semantic_score: float
    hybrid_score: float
