# Data and search

## OpenLibrary pipeline

The application keeps large local inputs outside Git. `data/` contains fetched or processed OpenLibrary data, while `db_source/` contains large dump files. The main import entry point is:

```bash
python -m backend.app.scripts.pipeline.run_import
```

The pipeline uses fetchers under `backend/app/scripts/openlibrary/`, cleaning and import modules under `processing/` and `importing/`, and relationship creation for books and authors. Run update jobs as controlled maintenance tasks:

```bash
python -m backend.app.scripts.updating.update_existing_books
python -m backend.app.scripts.updating.update_existing_authors
python -m backend.app.scripts.updating.update_books_from_edition_dump
python -m backend.app.scripts.updating.update_authors_from_wikidata_dump
python -m backend.app.scripts.updating.normalize_book_languages
```

Dump-based jobs require the corresponding files under `db_source/`; fetch and import jobs may require files under `data/`. Check logs and input availability before starting a long job. Do not run large imports or embedding backfills in a web request.

## Database preparation

Apply `backend/app/database/schema.sql` first. Feature migrations live under `backend/scripts/migrations/`:

- `add_user_roles_and_oauth_columns.sql` — role and OAuth account fields.
- `add_conversation_indexes.sql` — conversation query indexes.
- `add_book_embeddings.sql` — vector storage and indexes for book embeddings.
- `add_book_search_vector.sql` — PostgreSQL full-text search data/indexes.
- `library_schema_v2.sql` and other files — inspect before applying to an existing database because migration history is not managed by an ORM.

Semantic search requires pgvector and populated book embeddings. Hybrid search additionally requires the full-text migration.

## Embeddings

Supported providers are:

- `openai` with `text-embedding-3-small` and `OPENAI_API_KEY`.
- `local` with `sentence-transformers/all-MiniLM-L6-v2` and the optional `sentence-transformers` package.

Configure `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL_NAME`, and `EMBEDDING_DIMENSIONS`. The vector dimension must match the PostgreSQL column; the current default configuration is `384`. Embedding input is assembled from book title, description, authors, tags, languages, and publishers.

Redis can cache generated embeddings when configured. If Redis is unavailable, the application can continue without the optional cache.

## Backfill and retrieval

After applying the embeddings migration, backfill incrementally:

```bash
python -m backend.app.scripts.updating.backfill_book_embeddings --limit 100
```

Validate a small batch before removing `--limit`. Semantic search cannot return useful results for books without embeddings. Hybrid search combines keyword and semantic scores; adjust `keyword_weight` and `semantic_weight` at the API boundary only after validating result quality.

When book metadata changes, plan for the affected embeddings and any full-text search values to be refreshed. For provider changes, verify model output dimensions before applying a new backfill to an existing vector column.
