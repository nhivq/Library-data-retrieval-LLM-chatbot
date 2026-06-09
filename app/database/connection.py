# ---------- PostgreSQL connection ----------
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def get_connection():
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

    
# ---------- Database Dependency ----------
# -> Avoid conn.close() to be repeated inside every endpoint.
def get_db():

    conn = get_connection()

    try:
        yield conn

    finally:
        conn.close()

# Always use try/finally to guarantee resources are cleaned up even if an error occurs
# Otherwise, cursor or connections might remain open and cause resource leaks