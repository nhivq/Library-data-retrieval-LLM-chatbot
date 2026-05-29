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

Clone repo
```bash
git clone your-repo-url
```

Create venv:
```bash
python -m venv .venv
source .venv/bin/activate
```

Install packages:
```bash
pip install -r requirements.txt
```

Create database
```bash
createdb -U postgres book_db
```
Run schema.sql
```bash
psql -U postgres -d book_db -f database/schema.sql
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
