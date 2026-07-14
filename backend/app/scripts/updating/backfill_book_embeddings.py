import argparse
from pathlib import Path
import sys

from psycopg2.extras import RealDictCursor, execute_batch
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.connection import get_connection
from backend.app.semantic.embeddings import embed_text, format_vector
from backend.app.services.book_service import build_book_embedding_text


BATCH_SIZE = 100


def fetch_books_without_embeddings(cursor, limit):

    query = """
            SELECT b.work_key,
                   b.title,
                   b.description,
                   b.tags,
                   b.languages,
                   b.publishers,
                   COALESCE(
                       ARRAY_AGG(a.author_name)
                       FILTER (WHERE a.author_name IS NOT NULL),
                       ARRAY[]::text[]
                   ) AS authors

            FROM books b

                     LEFT JOIN book_authors ba
                           ON b.work_key = ba.work_key

                     LEFT JOIN authors a
                           ON ba.author_key = a.author_key

            WHERE b.embedding IS NULL

            GROUP BY b.work_key,
                     b.title,
                     b.description,
                     b.tags,
                     b.languages,
                     b.publishers

            ORDER BY b.work_key

            LIMIT %s
            """

    cursor.execute(query, (limit,))

    return cursor.fetchall()


def update_embeddings(cursor, rows):

    query = """
            UPDATE books
            SET embedding = %(embedding)s::vector
            WHERE work_key = %(work_key)s
            """

    execute_batch(
        cursor,
        query,
        rows,
        page_size=BATCH_SIZE
    )


def backfill_embeddings(limit, batch_size):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    total_updated = 0

    try:

        while True:

            books = fetch_books_without_embeddings(
                cursor,
                batch_size
            )

            if not books:
                break

            rows = []

            for book in tqdm(
                books,
                desc="Embedding books",
                unit="book"
            ):
                text = build_book_embedding_text(book)

                if not text:
                    continue

                rows.append(
                    {
                        "work_key": book["work_key"],
                        "embedding": format_vector(
                            embed_text(text)
                        )
                    }
                )

            update_embeddings(
                cursor,
                rows
            )

            conn.commit()

            total_updated += len(rows)

            if limit and total_updated >= limit:
                break

        return total_updated

    except Exception:

        conn.rollback()

        raise

    finally:

        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE
    )

    args = parser.parse_args()

    total_updated = backfill_embeddings(
        limit=args.limit,
        batch_size=args.batch_size
    )

    print(
        f"Updated embeddings for {total_updated} books"
    )


if __name__ == "__main__":
    main()
