# ---------- PostgreSQL connection ----------
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def get_connection():
    """Create a psycopg2 connection from DATABASE_URL or local env settings."""

    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg2.connect(database_url)

    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "book_db"),
        user=os.getenv("POSTGRES_USER", "book_user"),
        password=os.getenv("POSTGRES_PASSWORD", "123456"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

    
def get_db():
    """FastAPI dependency that yields one connection and always closes it."""

    conn = get_connection()

    try:
        yield conn

    finally:
        conn.close()
