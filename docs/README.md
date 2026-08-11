# Project documentation

This documentation describes the OpenLibrary AI book retrieval chatbot as it exists in this repository. It is organized around the workflows needed to develop, extend, operate, and deploy the application.

## Start here

- [Setup and development](setup.md) — install dependencies, configure services, run locally, or use Docker Compose.
- [Architecture](architecture.md) — understand the frontend, API, database, cache, LLM, and tool flow.

## Use and extend the application

- [API reference](api.md) — route groups, authentication, request patterns, and streaming chat.
- [Data and search](data-and-search.md) — OpenLibrary imports, migrations, embeddings, semantic search, and hybrid search.

## Operate and deploy

- [Operations](operations.md) — tests, logs, maintenance jobs, deployment responsibilities, and troubleshooting.

The root [README](../README.md) remains the concise project overview. The application exposes interactive API documentation at `/docs` and its OpenAPI schema at `/openapi.json` when the backend is running.

## Scope

This set intentionally omits product-management, multi-tenant, plugin, billing, and other enterprise documentation that does not apply to this project. Keep claims tied to source files and current deployment configuration.
