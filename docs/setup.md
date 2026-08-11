# Setup and development

## Prerequisites

- Python 3.12
- Node.js and npm
- PostgreSQL with the `pgvector` extension, or Docker
- An OpenRouter key for chat
- An OpenAI key when `EMBEDDING_PROVIDER=openai`

The backend dependencies are listed in the root `requirements.txt`. The same file is copied by `Dockerfile` during the image build.

## Configure the environment

```bash
cp .env.example .env
```

Set real secrets in `.env`; never commit that file. Common settings are:

```env
OPENROUTER_API_KEY=...
DATABASE_URL=postgresql://user:password@localhost:5432/book_db
JWT_SECRET_KEY=...
SESSION_SECRET_KEY=...
FRONTEND_URL=http://127.0.0.1:5173
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=...
EMBEDDING_MODEL_NAME=text-embedding-3-small
EMBEDDING_DIMENSIONS=384
```

`DATABASE_URL` takes precedence over individual `POSTGRES_*` settings. Redis is optional; set `CACHE_ENABLED=false` to disable its use explicitly. Google OAuth additionally requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and a matching `GOOGLE_REDIRECT_URI`.

## Manual development

Create and activate a virtual environment from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Prepare a PostgreSQL database with pgvector, then apply the base schema and feature migrations in order:

```bash
psql "$DATABASE_URL" -f backend/app/database/schema.sql
psql "$DATABASE_URL" -f backend/scripts/migrations/add_user_roles_and_oauth_columns.sql
psql "$DATABASE_URL" -f backend/scripts/migrations/add_conversation_indexes.sql
psql "$DATABASE_URL" -f backend/scripts/migrations/add_book_embeddings.sql
psql "$DATABASE_URL" -f backend/scripts/migrations/add_book_search_vector.sql
```

Start the API from the repository root:

```bash
uvicorn backend.app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `http://127.0.0.1:8000/docs`.

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

The Vite frontend runs at `http://127.0.0.1:5173`. Use `VITE_API_BASE` when the API is elsewhere:

```bash
VITE_API_BASE=http://127.0.0.1:8000 npm run dev
```

## Docker Compose

Compose starts the backend, PostgreSQL with pgvector, and Redis. The frontend remains a separate Vite process.

```bash
cp .env.example .env
docker compose up --build
```

The API is exposed on port `8000`, Redis on `6379`, and PostgreSQL is initialized from `backend/app/database/schema.sql` on first creation of the named `postgres_data` volume. Compose supplies service-to-service database and Redis URLs; review `docker-compose.yml` before using it outside local development.
