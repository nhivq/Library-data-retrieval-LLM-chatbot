-- =========================
-- BOOK EMBEDDINGS
-- =========================

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE books
ADD COLUMN IF NOT EXISTS embedding vector(384);

CREATE INDEX IF NOT EXISTS idx_books_embedding
ON books
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
