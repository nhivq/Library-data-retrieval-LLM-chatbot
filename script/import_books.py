import json
import psycopg2
from psycopg2.extras import execute_batch

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="book_db",
    user="book_user",
    password="123456",
    host="localhost",
    port="5432"
)

# Open a cursor to perform db operations
cur = conn.cursor()

# IMPORT AUTHORS
with open("../data/authors.json", "r", encoding="utf-8") as f:
    authors = json.load(f)
valid_author_keys = set(authors.keys())

authors_data = []

for author_key, author_name in authors.items():
    authors_data.append((author_key, author_name))

execute_batch(
    cur,
    """
    INSERT INTO authors
    (author_key, author_name)

    VALUES (%s,%s)

    ON CONFLICT (author_key)
    DO NOTHING
    """,
    authors_data,
    page_size=1000
)
print("Authors imported")

# IMPORT BOOKS
with open("../data/books.json", "r", encoding="utf-8") as f:
    books=json.load(f)

book_data=[]
relationship_data=[]

for book in books:
    book_data.append((book["work_key"], book["title"], book["tags"], book["publish_date"], book["rating"]))

    missing_authors = 0

    for author_key in book["author_keys"]:
        if author_key in valid_author_keys:
            relationship_data.append((book["work_key"], author_key))
        else:
            missing_authors += 1

print(f"Skipped {missing_authors} missing author references")

execute_batch(
cur,
"""
INSERT INTO books
(work_key,title,tags,publish_date,rating)

VALUES (%s,%s,%s,%s,%s)

ON CONFLICT (work_key)
DO NOTHING
""",
book_data,
page_size=1000
)

execute_batch(
cur,

"""
INSERT INTO book_authors
(work_key,author_key)

VALUES(%s,%s)

ON CONFLICT
DO NOTHING
""",

relationship_data,
page_size=1000
)
print("Books imported")


conn.commit()

cur.close()
conn.close()

print("Done")