# Architecture

## Runtime flow

```text
Browser
  │ HTTP, bearer tokens, and SSE
  ▼
React/Vite frontend ──► FastAPI backend
                          ├── PostgreSQL + pgvector
                          ├── optional Redis cache
                          ├── OpenRouter LLM
                          └── in-process FastMCP tools
```

Production commonly separates responsibilities across Vercel (frontend), Render (backend), and Neon or another pgvector-capable PostgreSQL provider. Docker Compose provides a local backend, database, and Redis stack; it does not serve the frontend.

## Backend boundaries

The canonical application is `backend/app/main.py`, started with `uvicorn backend.app.main:app`. It configures request logging, request IDs, signed sessions for OAuth, CORS, and routers under `backend/app/routes/`.

- `core/` — configuration, security dependencies, logging, and cache helpers.
- `routes/` — HTTP transport and dependency wiring.
- `schemas/` — Pydantic request and response models.
- `services/` — database queries and business logic.
- `database/` — PostgreSQL connections and the base schema.
- `semantic/` — embedding providers and vector formatting.
- `llm/` — OpenRouter client, prompts, streaming agent loop, and tool conversion.
- `mcp_integration/` — FastMCP server and client integration.
- `scripts/` — OpenLibrary ingestion and maintenance jobs.

The top-level `app/main.py` is a compatibility wrapper that re-exports the canonical application. The Docker image uses `backend.app.main:app`.

## Chat and tool flow

`POST /chat` authenticates the user, then streams Server-Sent Events from the agent loop in `backend/app/llm/llm_client.py`. The loop loads conversation history and FastMCP tool schemas, sends the request to OpenRouter, executes any requested tools, compacts tool results, and continues until a response is complete or the iteration limit is reached. Messages and tool activity are persisted through the conversation services.

The FastMCP server in `backend/app/mcp_integration/server.py` exposes book, author, recommendation, semantic-search, hybrid-search, bookmark, authentication, and conversation operations. The backend injects the authenticated user ID into user-specific operations instead of allowing the model to select an account.

## Retrieval flow

Metadata searches and recommendations use PostgreSQL service queries. Semantic search creates a normalized embedding for the query and compares it with stored book vectors using pgvector. Hybrid search combines PostgreSQL full-text relevance with vector similarity and supports metadata filters. Embedding generation can use OpenAI or a local Sentence Transformers model; the configured dimension must match the database vector column.

## Frontend responsibilities

The React application in `frontend/src/` handles authentication pages, conversations, streamed chat output, bookmarks, book cards, and admin analytics. `frontend/src/api/client.js` adds bearer tokens, performs one refresh retry after a 401 response, and uses `VITE_API_BASE` to select the backend. `frontend/vercel.json` rewrites client-side routes to `index.html` for SPA hosting.
