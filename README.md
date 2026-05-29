# LLM Book Retrieval Backend

### Learning-focused LLM book retrieval system using:

- FastAPI
- PostgreSQL
- Raw SQL (psycopg2)

### Current features:

- Get books
- Search books
- Book details
- Author details
- Bookmarks

### Setup

Create venv:
```bash
python -m venv .venv
```

Install packages:
```bash
pip install -r requirements.txt
```

Import data:
```bash
python scripts/import_books.py
```

Run project:
```bash
uvicorn app.main:app --reload
```

Open Swagger:
```text
http://127.0.0.1:8000/docs
```

Open frontend:
```text
frontend/login.html
```
