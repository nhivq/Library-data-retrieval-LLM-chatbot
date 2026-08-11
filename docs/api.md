# API reference

Run the backend and use the generated reference at `/docs` or `/openapi.json`. The routes below are registered by `backend/app/main.py`.

## Authentication

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | No | Create a username/password account. |
| `POST` | `/auth/login` | No | Return access and refresh tokens. |
| `POST` | `/auth/refresh` | No | Exchange a refresh token for an access token. |
| `GET` | `/auth/me` | Bearer | Return the current user. |
| `GET` | `/auth/google` | No | Start Google OAuth. |
| `GET` | `/auth/google/callback` | No | Complete OAuth and redirect to the frontend. |

Authenticated JSON requests use `Authorization: Bearer <access-token>`. The frontend stores access and refresh tokens locally and retries one expired access token through `/auth/refresh`.

## Books

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/books/` | Browse books; `limit` defaults to 10 and is capped at 100. |
| `GET` | `/books/search` | Metadata search using `q`, `author`, `min_rating`, `tag`, and publication-year filters, with `page` and `limit`. |
| `GET` | `/books/recommendations` | Recommend from a natural-language `prompt`, optional repeated `concept_groups`, and `limit`. |
| `GET` | `/books/top-rated-by-tag` | Get top-rated books for a required `tag`. |
| `GET` | `/books/semantic-search` | Vector search for a required `query`. |
| `GET` | `/books/hybrid-search` | Combine keyword and vector search using `query`, weights, and optional metadata filters. |
| `GET` | `/books/{work_key:path}` | Fetch one OpenLibrary work. |
| `GET` | `/books/{work_key:path}/similar` | Find metadata-similar books. |

The `path` converter is intentional: OpenLibrary work keys contain slashes.

## Authors

- `GET /authors/` — paginated author list using `page` and `limit`.
- `GET /authors/search` — search with `author_name` or `author_key`.
- `GET /authors/{author_key:path}` — fetch one author.

## Bookmarks

All bookmark routes are scoped to the authenticated user:

- `GET /bookmarks/` — list bookmarks.
- `POST /bookmarks/` — save a bookmark with a `work_key` body.
- `DELETE /bookmarks/{work_key:path}` — remove one bookmark.

## Chat and conversations

- `POST /chat` — authenticated request with a chat message, optional `session_id`, and optional `edited_message_id`; response media type is `text/event-stream`.
- `GET /conversations/` — list the current user's sessions.
- `GET /conversations/{session_id}` — retrieve messages for one session.
- `DELETE /conversations/` — delete all conversations owned by the current user.
- `DELETE /conversations/{session_id}` — delete one conversation owned by the current user.

Chat events are emitted as SSE records. The frontend handles progress, user-message, text-delta, and completion events; use the live endpoint or `frontend/src/pages/ChatPage.jsx` for the exact payload fields.

## Administration

`GET /admin/analytics` requires an authenticated user with the `admin` role.

## Errors and inspection

Route handlers return JSON error details with HTTP status codes such as `400`, `401`, `404`, and `503`. Semantic and hybrid search can return `503` when embeddings or required retrieval capabilities are unavailable. FastAPI validates query and body fields before the service layer runs.

Use `/openapi.json` as the machine-readable contract and `/docs` to try requests against the running instance. Keep the generated schema as the authority when a prose summary and implementation diverge.
