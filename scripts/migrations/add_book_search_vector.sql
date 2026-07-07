ALTER TABLE books
ADD COLUMN IF NOT EXISTS search_vector tsvector;

UPDATE books
SET search_vector =
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(array_to_string(tags, ' '), '')), 'C') ||
    setweight(to_tsvector('english', coalesce(array_to_string(languages, ' '), '')), 'D') ||
    setweight(to_tsvector('english', coalesce(array_to_string(publishers, ' '), '')), 'D');

CREATE INDEX IF NOT EXISTS idx_books_search_vector 
ON books 
USING GIN (search_vector);