# ---------- PostgreSQL connection ----------
import psycopg2

def get_connection():

    conn = psycopg2.connect(
        dbname="book_db",
        user="book_user",
        password="123456",
        host="localhost",
        port="5432"
    )

    return conn

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