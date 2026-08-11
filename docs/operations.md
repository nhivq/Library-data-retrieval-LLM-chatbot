# Operations and deployment

## Tests

Run the backend tests from the repository root:

```bash
pytest backend/app/tests
```

The tests use database fakes for service behavior and do not require live PostgreSQL or Redis. They cover authentication, books, bookmarks, conversations, analytics, caching, logging, and selected route dependency behavior. Chat SSE, MCP execution, OAuth, real migrations, embedding backfills, and frontend behavior are not fully covered by this suite; validate those paths manually when changing them.

## Logs and request tracing

The canonical FastAPI app creates or accepts an `X-Request-ID`, adds it to the response, and logs request completion with method, path, and status. Preserve that header when investigating a request across backend logs and a frontend report.

## Cache behavior

Redis is a read-through cache for optional application data and embeddings. Configure `REDIS_URL`, `CACHE_ENABLED`, and `CACHE_DEBUG`. A Redis outage should not prevent the API from serving uncached requests; disable the cache explicitly while diagnosing cache-specific problems.

## Deployment responsibilities

### Docker Compose

Use Compose for local backend, pgvector PostgreSQL, and Redis development:

```bash
docker compose up --build
```

The frontend is started separately with Vite. Compose initializes the database schema when the PostgreSQL volume is created; existing volumes are not reinitialized automatically.

### Render or another container host

Build from the repository root using the root `requirements.txt`. Start the ASGI app with:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

Set production secrets and URLs explicitly. Use an OpenAI embedding provider in memory-constrained web services unless local model loading has been tested for the selected instance.

### Neon or another PostgreSQL provider

Use a provider with pgvector support. Apply the base schema and required migrations before enabling semantic or hybrid search. Populate embeddings before presenting semantic results to users.

### Vercel

Deploy the `frontend/` directory as the Vite site. Set `VITE_API_BASE` to the backend origin. `frontend/vercel.json` rewrites client-side routes to `index.html`. Set the backend CORS allowlist and `FRONTEND_URL` to the deployed frontend origin, and use a matching Google OAuth callback URL if OAuth is enabled.

## Troubleshooting checklist

- `ModuleNotFoundError`: run commands from the repository root and use `backend.app...` module paths.
- API starts but chat fails: verify `OPENROUTER_API_KEY`, database connectivity, and that the authenticated request has a valid bearer token.
- Semantic search returns an availability error: check pgvector, the embeddings migration, provider credentials, model dimension, and backfill status.
- Hybrid search is empty or unavailable: verify both embeddings and the full-text migration.
- OAuth redirects incorrectly: compare `GOOGLE_REDIRECT_URI`, `FRONTEND_URL`, Google Console settings, and CORS origins.
- Frontend calls the wrong host: inspect `VITE_API_BASE` and the browser network request.
- Compose changes do not affect the database: remember that an existing `postgres_data` volume is not reinitialized automatically.

Never commit `.env`, API keys, OAuth secrets, database credentials, dump files, or other ignored local data.
