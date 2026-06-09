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

Create a local .env file:
```bash
cp .env.example .env
```
Set your `OPENROUTER_API_KEY` in `.env` before running the app.

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
python script/import_books.py
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

HTTP server
```text
http://10.6.200.83:8080/
```

## Deploying on Render

1. Add a Render web service with the repository.
2. Set the following env vars in Render:
   - `OPENROUTER_API_KEY`
   - `DATABASE_URL`
3. Use this build command:
   ```bash
   pip install -r requirements.txt
   ```
4. Use this start command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
