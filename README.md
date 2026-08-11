# OpenLibrary AI Book Retrieval Chatbot

A full-stack book discovery application built from OpenLibrary data. Users can search books and authors, ask an AI assistant for recommendations, save bookmarks, and continue previous conversations.

The application consists of a FastAPI backend, PostgreSQL with pgvector, optional Redis caching, an OpenRouter-powered LLM with FastMCP tools, and a React/Vite frontend.

See the [project documentation](docs/README.md) for focused setup, architecture, API, data/search, and operations guides.

## Features

- Metadata search by title, author, tag, rating, and publication year
- Concept-aware recommendations and similar-book discovery
- Semantic search with OpenAI or local Sentence Transformers embeddings
- Hybrid search combining PostgreSQL full-text search and vector similarity
- User registration, JWT access/refresh tokens, and Google OAuth
- Authenticated bookmarks
- Streaming chat responses over Server-Sent Events
- Conversation history and deletion
- Admin analytics for collection and data quality statistics
- OpenLibrary import, processing, and update scripts

## Architecture

```text
React + Vite frontend
          |
          | HTTP, JWT, SSE
          v
FastAPI backend ---- OpenRouter / OpenAI
          |
          +---- PostgreSQL + pgvector
          +---- Redis cache
          +---- FastMCP tools
```

## Technology

- Python 3.12
- FastAPI, Starlette, Pydantic, Uvicorn
- PostgreSQL and psycopg2
- pgvector for semantic search
- Redis for optional read-through caching
- OpenRouter through the OpenAI-compatible client
- FastMCP for LLM tool execution
- React 18 and Vite 6
- Neon, Render, and Vercel are supported deployment targets

## Repository Layout

```text
.
├── backend/
│   ├── app/
│   │   ├── core/                 Configuration, security, cache, logging
│   │   ├── database/             PostgreSQL connection and base schema
│   │   ├── llm/                  OpenRouter client, prompts, tool handling
│   │   ├── mcp_integration/      FastMCP server and client
│   │   ├── routes/               API routers
│   │   ├── schemas/              Pydantic models
│   │   ├── scripts/              OpenLibrary import and update jobs
│   │   ├── semantic/             Embedding helpers
│   │   ├── services/             Database and business logic
│   │   └── tests/                Pytest unit and route tests
│   └── requirements.txt
├── frontend/
│   ├── src/                      React pages, components, and API client
│   ├── package.json
│   └── vercel.json               SPA rewrite configuration
├── data/                         Local OpenLibrary data (ignored by Git)
├── db_source/                    Large source dumps (ignored by Git)
├── docker-compose.yml            Backend, PostgreSQL, and Redis services
├── Dockerfile                    Backend image definition
└── requirements.txt              Root Python dependency file
```

`app/main.py` is a compatibility entry point for hosts that run `uvicorn app.main:app`. The application implementation is in `backend/app/main.py`.

## Configuration

Create a local environment file:

```bash
cp .env.example .env
```

Set the values required by the services you use:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
DATABASE_URL=postgresql://book_user:123456@localhost:5432/book_db

JWT_SECRET_KEY=replace_with_a_long_random_value
SESSION_SECRET_KEY=replace_with_a_long_random_value

FRONTEND_URL=http://127.0.0.1:5173
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback

REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
CACHE_DEBUG=false

EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
EMBEDDING_MODEL_NAME=text-embedding-3-small
EMBEDDING_DIMENSIONS=384
```

`DATABASE_URL` takes precedence over the individual `POSTGRES_*` settings. If it is not set, the database connection uses these defaults:

```env
POSTGRES_DB=book_db
POSTGRES_USER=book_user
POSTGRES_PASSWORD=123456
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Redis is optional. If it is unavailable, the API continues without the cache. Set `CACHE_ENABLED=false` to disable it explicitly.

## Local Development

### 1. Install backend dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Prepare PostgreSQL

PostgreSQL must have the pgvector extension available for semantic search. Create the database and apply the base schema:

```bash
createdb book_db
psql "$DATABASE_URL" -f backend/app/database/schema.sql
```

Apply migrations required by the features you enable:

```bash
psql "$DATABASE_URL" -f backend/scripts/migrations/add_user_roles_and_oauth_columns.sql
psql "$DATABASE_URL" -f backend/scripts/migrations/add_conversation_indexes.sql
psql "$DATABASE_URL" -f backend/scripts/migrations/add_book_embeddings.sql
psql "$DATABASE_URL" -f backend/scripts/migrations/add_book_search_vector.sql
```

### 3. Run the backend

From the repository root:

```bash
uvicorn backend.app.main:app --reload
```

The API and interactive documentation are available at `http://127.0.0.1:8000` and `http://127.0.0.1:8000/docs`.

### 4. Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://127.0.0.1:5173`. Set `VITE_API_BASE` when using a backend at a different address:

```bash
VITE_API_BASE=http://127.0.0.1:8000 npm run dev
```

### Docker Compose

Docker Compose starts the backend, PostgreSQL with pgvector, and Redis:

```bash
cp .env.example .env
docker compose up --build
```

The API is exposed on port `8000` and Redis on port `6379`. The PostgreSQL data is stored in the `postgres_data` named volume. The frontend is still run separately with the Vite commands above.

## Data Import and Maintenance

The main OpenLibrary import pipeline is located in `backend/app/scripts`:

```bash
python -m backend.app.scripts.pipeline.run_import
```

Available update jobs include:

```bash
python -m backend.app.scripts.updating.update_existing_books
python -m backend.app.scripts.updating.update_existing_authors
python -m backend.app.scripts.updating.update_books_from_edition_dump
python -m backend.app.scripts.updating.update_authors_from_wikidata_dump
python -m backend.app.scripts.updating.normalize_book_languages
```

These jobs may require OpenLibrary data in `data/` or large dump files in `db_source/` and can take a long time. Run them as controlled maintenance jobs rather than during web requests.

## Semantic and Hybrid Search

Semantic search supports:

- `openai` using `text-embedding-3-small`
- `local` using `sentence-transformers/all-MiniLM-L6-v2`

For local embeddings, install the optional dependency:

```bash
pip install sentence-transformers
```

The configured embedding dimension must match the PostgreSQL vector column. The current default is `384`.

After applying `add_book_embeddings.sql`, backfill embeddings in small batches:

```bash
python -m backend.app.scripts.updating.backfill_book_embeddings --limit 100
```

Remove `--limit` only after validating the process against the complete dataset. Semantic search requires embeddings to be populated. Hybrid search additionally requires `add_book_search_vector.sql`.

## API Overview

Authentication:

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
GET  /auth/me
GET  /auth/google
GET  /auth/google/callback
```

Books:

```text
GET /books/
GET /books/search
GET /books/recommendations
GET /books/top-rated-by-tag
GET /books/semantic-search
GET /books/hybrid-search
GET /books/{work_key}
GET /books/{work_key}/similar
```

Authors:

```text
GET /authors/
GET /authors/search
GET /authors/{author_key}
```

Bookmarks and conversations:

```text
GET    /bookmarks/
POST   /bookmarks/
DELETE /bookmarks/{work_key}

POST   /chat
GET    /conversations/
GET    /conversations/{session_id}
DELETE /conversations/
DELETE /conversations/{session_id}
```

Administration:

```text
GET /admin/analytics
```

Admin endpoints require an authenticated user whose role is `admin`. The `POST /chat` response is streamed as SSE events.

## LLM Tools

The chat agent uses an in-process FastMCP server. Tools cover book and author search, recommendations, semantic and hybrid search, book details, similar books, bookmark management, conversation deletion, registration, and login.

The backend supplies the authenticated user ID to user-specific tools instead of allowing the model to choose the account being modified.

## Testing

Run the backend test suite from the repository root:

```bash
pytest backend/app/tests
```

The tests use database fakes for service behavior and do not require a running PostgreSQL or Redis instance.

## Deployment

- Build the backend from the repository root with `pip install -r requirements.txt`.
- Start the backend with `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
- Deploy the `frontend/` directory as a Vercel static site.
- Set the frontend `VITE_API_BASE` to the deployed backend URL.
- Set the backend `FRONTEND_URL` to the deployed frontend origin and configure matching CORS and Google OAuth redirect URLs.
- Use a PostgreSQL provider with pgvector support, such as Neon, for semantic and hybrid search.
- Use `EMBEDDING_PROVIDER=openai` in memory-constrained web services unless local embeddings are explicitly configured.

Never commit `.env`, API keys, OAuth secrets, or database credentials.
