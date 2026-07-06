# OpenLibrary AI Book Retrieval Chatbot

A full-stack book discovery app built on OpenLibrary data. The project combines a FastAPI backend, PostgreSQL, JWT authentication, a vanilla JavaScript frontend, OpenRouter-powered chat, FastMCP tools, and semantic book search with `sentence-transformers` + `pgvector`.

The chatbot can search books and authors, manage user bookmarks, remember conversation history, recommend books by mood/taste, and perform vector-based semantic search for conceptual queries such as "books about friendship after war".

## Features

- Book search by title, author, tag, rating, and publication year.
- Author search and author detail lookup.
- Book details and similar-book recommendations.
- User registration, login, JWT refresh tokens, and Google OAuth.
- Authenticated bookmarks.
- Streaming AI chat over Server-Sent Events.
- Conversation history with readable titles and delete support.
- Admin analytics dashboard for data quality and collection stats.
- LLM tool calling through FastMCP.
- Recommendation search using concept-group ranking.
- Semantic vector search using Sentence Transformers and pgvector.
- Data import/update scripts for OpenLibrary works, editions, authors, languages, and Wikidata enrichment.

## Tech Stack

- Backend: FastAPI, Starlette, Pydantic
- Database: PostgreSQL, psycopg2, raw SQL
- Auth: JWT, bcrypt, Google OAuth via Authlib
- LLM: OpenRouter through the OpenAI-compatible client
- Tool layer: FastMCP
- Semantic search: sentence-transformers, pgvector
- Frontend: HTML, CSS, vanilla JavaScript
- Deployment target: Render backend, Vercel/static frontend

## Project Structure

```text
app/
  core/                 # Config, auth dependencies, JWT helpers
  database/             # PostgreSQL connection and schema
  llm/                  # OpenRouter client, streaming agent, prompts, tool processing
  mcp_integration/      # FastMCP tool server used by the LLM
  routes/               # FastAPI routers
  schemas/              # Pydantic request/response models
  semantic/             # Embedding model helpers
  services/             # SQL/business logic

frontend/
  index.html            # Login page
  register.html         # Registration page
  chat.html             # Main chat UI
  admin.html            # Admin dashboard
  *.js / *.css          # Vanilla frontend logic and styling

scripts/
  pipeline/             # Main OpenLibrary import pipeline
  importing/            # Import helpers
  processing/           # Cleaning/normalization helpers
  updating/             # Update/backfill scripts
  migrations/           # SQL migrations
  validation/           # Data validation scripts
```

## Environment Variables

Create a local `.env` file:

```bash
cp .env.example .env
```

Recommended variables:

```env
DATABASE_URL=postgresql://book_user:123456@localhost:5432/book_db

JWT_SECRET_KEY=change_me
SESSION_SECRET_KEY=change_me

OPENROUTER_API_KEY=your_openrouter_api_key

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback

FRONTEND_URL=http://127.0.0.1:5500/frontend
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

If `DATABASE_URL` is not set, the app falls back to:

```env
POSTGRES_DB=book_db
POSTGRES_USER=book_user
POSTGRES_PASSWORD=123456
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## Local Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the database:

```bash
createdb book_db
```

Apply the base schema:

```bash
psql "$DATABASE_URL" -f app/database/schema.sql
```

Apply optional migrations as needed:

```bash
psql "$DATABASE_URL" -f scripts/migrations/add_user_roles_and_oauth_columns.sql
psql "$DATABASE_URL" -f scripts/migrations/add_book_embeddings.sql
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

Open API docs:

```text
http://127.0.0.1:8000/docs
```

Serve the frontend from the project root:

```bash
python -m http.server 5500
```

Then open:

```text
http://127.0.0.1:5500/frontend/index.html
```

## Data Import and Updates

The project includes scripts for importing and enriching OpenLibrary data.

Main import entry point:

```bash
python scripts/pipeline/run_import.py
```

Useful update scripts:

```bash
python scripts/updating/update_existing_books.py
python scripts/updating/update_existing_authors.py
python scripts/updating/update_books_from_edition_dump.py
python scripts/updating/update_authors_from_wikidata_dump.py
python scripts/updating/normalize_book_languages.py
```

Data validation:

```bash
python scripts/validation/validate_books.py
python scripts/validation/validate_authors.py
```

Some update scripts scan large OpenLibrary dump files in `db_source/`, so they can take a long time.

## Semantic Search Setup

Semantic search uses:

- `sentence-transformers/all-MiniLM-L6-v2`
- 384-dimensional embeddings
- PostgreSQL `pgvector`
- cosine similarity with `<=>`

Apply the pgvector migration:

```bash
psql "$DATABASE_URL" -f scripts/migrations/add_book_embeddings.sql
```

Backfill embeddings:

```bash
python scripts/updating/backfill_book_embeddings.py --limit 100
```

Remove `--limit` when ready to embed the full dataset:

```bash
python scripts/updating/backfill_book_embeddings.py
```

Test semantic search:

```http
GET /books/semantic-search?query=books about friendship after war
```

The semantic text for each book is built from title, description, authors, tags, languages, and publishers.

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
GET /books/semantic-search
GET /books/{work_key}
GET /books/{work_key}/similar
```

Authors:

```text
GET /authors/
GET /authors/search
GET /authors/{author_key}
```

Bookmarks:

```text
GET    /bookmarks/
POST   /bookmarks/
DELETE /bookmarks/{work_key}
```

Chat and conversations:

```text
POST   /chat
GET    /conversations/
GET    /conversations/{session_id}
DELETE /conversations/
DELETE /conversations/{session_id}
```

Admin:

```text
GET /admin/analytics
```

Admin routes require a user with `role = 'admin'`.

## LLM Tooling

The chat endpoint streams responses from the LLM and allows tool use through FastMCP. Current tools include:

- `search_books`
- `recommend_books`
- `semantic_search_books`
- `get_book`
- `similar_books`
- `search_authors`
- `get_author`
- `save_bookmarks`
- `get_bookmarks`
- `delete_bookmarks`
- `delete_all_conversations`
- `register`
- `login`

The backend injects the authenticated `user_id` for tools that modify user data, so the model does not decide which user's bookmarks or conversations to access.

## Frontend

The frontend is intentionally simple and framework-free.

- `auth.js`: API base URL, token storage, refresh-token retry, auth guards.
- `chat.js`: chat UI, SSE parsing, markdown rendering, welcome state.
- `sidebar.js`: conversation history and bookmarks.
- `admin.js`: analytics dashboard.

For local development, update `API_BASE` in `frontend/auth.js` if needed.

## Deployment Notes

Backend on Render:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required Render environment variables:

```text
DATABASE_URL
JWT_SECRET_KEY
SESSION_SECRET_KEY
OPENROUTER_API_KEY
FRONTEND_URL
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI
```

After changing MCP tools, prompts, or dependencies, restart/redeploy the backend so the LLM sees the new tool schema.

## Notes and Limitations

- The current recommendation endpoint is concept-aware but still SQL-based.
- True semantic search requires embeddings to be backfilled before `/books/semantic-search` returns results.
- `sentence-transformers` downloads the embedding model on first use, so first startup/search can be slower.
- Large embedding backfills should be run as a controlled background/admin task, not during normal web requests.
