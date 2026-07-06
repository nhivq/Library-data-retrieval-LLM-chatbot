import os


EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/all-MiniLM-L6-v2"
)

_embedding_model = None


def get_embedding_model():
    global _embedding_model

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


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()


def format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"
