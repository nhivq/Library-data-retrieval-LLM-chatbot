import os
from math import sqrt

from app.core.cache import get_json, make_cache_key, set_json


def resolve_embedding_provider() -> str:
    """Choose the embedding provider from env vars, with local as fallback."""

    configured_provider = os.getenv("EMBEDDING_PROVIDER")

    if configured_provider:
        return configured_provider.lower()

    if os.getenv("OPENAI_API_KEY"):
        return "openai"

    return "local"


EMBEDDING_PROVIDER = resolve_embedding_provider()

DEFAULT_LOCAL_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

EMBEDDING_MODEL_NAME = (
    os.getenv("EMBEDDING_MODEL_NAME")
    or (
        DEFAULT_OPENAI_EMBEDDING_MODEL
        if EMBEDDING_PROVIDER == "openai"
        else DEFAULT_LOCAL_EMBEDDING_MODEL
    )
)

EMBEDDING_DIMENSIONS = int(
    os.getenv(
        "EMBEDDING_DIMENSIONS",
        "384"
    )
)

_embedding_model = None
_openai_client = None
_logged_provider = False


def normalize_embedding(embedding: list[float]) -> list[float]:
    """Normalize a vector so cosine-style similarity behaves consistently."""

    length = sqrt(
        sum(
            value * value
            for value in embedding
        )
    )

    if length == 0:
        return embedding

    return [
        value / length
        for value in embedding
    ]


def get_embedding_model():
    """Lazy-load the local sentence-transformers model."""

    global _embedding_model

    # Render web services have tight startup expectations. Local embeddings can
    # be heavy, so require an explicit override there.
    if os.getenv("RENDER") and os.getenv("ALLOW_LOCAL_EMBEDDINGS_ON_RENDER") != "true":
        raise RuntimeError(
            "Local sentence-transformers embeddings are disabled on Render. "
            "Set EMBEDDING_PROVIDER=openai and OPENAI_API_KEY."
        )

    if _embedding_model is None:
        # Import this only when semantic search is actually used.
        # Loading sentence-transformers at app startup can delay Render
        # long enough that no web port is detected.
        try:
            from sentence_transformers import SentenceTransformer

        except Exception as e:
            raise RuntimeError(
                "Semantic search dependencies are not available"
            ) from e

        try:
            _embedding_model = SentenceTransformer(
                EMBEDDING_MODEL_NAME
            )

        except Exception as e:
            raise RuntimeError(
                "Semantic embedding model could not be loaded"
            ) from e

    return _embedding_model


def get_openai_client():
    """Lazy-load an OpenAI client for hosted embedding generation."""

    global _openai_client

    if _openai_client is None:
        try:
            from openai import OpenAI

        except Exception as e:
            raise RuntimeError(
                "OpenAI embedding dependencies are not available"
            ) from e

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai"
            )

        _openai_client = OpenAI(
            api_key=api_key
        )

    return _openai_client


def embed_text_local(text: str) -> list[float]:
    """Embed text with the local sentence-transformers model."""

    model = get_embedding_model()

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()


def embed_text_openai(text: str) -> list[float]:
    """Embed text with the configured OpenAI embedding model."""

    client = get_openai_client()

    response = client.embeddings.create(
        model=EMBEDDING_MODEL_NAME,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS
    )

    return normalize_embedding(
        response.data[0].embedding
    )


def embed_text(text: str) -> list[float]:
    """Embed text using the configured provider."""

    global _logged_provider

    if not _logged_provider:
        print(
            "Embedding provider:",
            EMBEDDING_PROVIDER,
            "model:",
            EMBEDDING_MODEL_NAME,
            "dimensions:",
            EMBEDDING_DIMENSIONS
        )
        _logged_provider = True

    cache_key = make_cache_key(
        "embedding",
        {
            "provider": EMBEDDING_PROVIDER,
            "model": EMBEDDING_MODEL_NAME,
            "dimensions": EMBEDDING_DIMENSIONS,
            "text": text
        }
    )

    cached_embedding = get_json(cache_key)

    if cached_embedding is not None:
        return cached_embedding

    if EMBEDDING_PROVIDER == "openai":
        embedding = embed_text_openai(text)

    else:
        embedding = embed_text_local(text)

    set_json(
        cache_key,
        embedding,
        ttl_seconds=60 * 60 * 24 * 30
    )

    return embedding


def format_vector(embedding: list[float]) -> str:
    """Format a Python list as the string literal expected by pgvector."""

    return "[" + ",".join(str(value) for value in embedding) + "]"
