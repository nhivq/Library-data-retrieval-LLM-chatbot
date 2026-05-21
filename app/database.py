# PostgreSQL connection

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