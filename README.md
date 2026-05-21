# LLM Book Retrieval Backend

Learning-focused LLM book retrieval system using:

- FastAPI
- PostgreSQL
- Raw SQL (psycopg2)

Current features:

- Get books
- Search books
- Book details
- Author details
- Bookmarks

Run project:

```bash
uvicorn app.main:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```