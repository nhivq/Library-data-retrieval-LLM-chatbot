from pathlib import Path
import sys

from psycopg2.extras import execute_batch
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database.connection import get_connection
from scripts.processing.language_names import normalize_languages


BATCH_SIZE = 1000


def fetch_books(cursor):

    cursor.execute(
        """
        SELECT work_key, languages
        FROM books
        WHERE languages IS NOT NULL
          AND cardinality(languages) > 0
        ORDER BY work_key
        """
    )

    return cursor.fetchall()


def normalize_book_languages(dry_run=False, batch_size=BATCH_SIZE):

    conn = get_connection()
    cursor = conn.cursor()

    rows = fetch_books(cursor)
    updates = []

    for work_key, languages in tqdm(
        rows,
        desc="Normalizing book languages",
        unit="book"
    ):
        normalized = normalize_languages(languages)

        if normalized != languages:
            updates.append(
                {
                    "work_key": work_key,
                    "languages": normalized,
                }
            )

    if updates and not dry_run:
        execute_batch(
            cursor,
            """
            UPDATE books
            SET languages = %(languages)s
            WHERE work_key = %(work_key)s
            """,
            updates,
            page_size=batch_size
        )

        conn.commit()

    else:
        conn.rollback()

    cursor.close()
    conn.close()

    print("Books with languages:", len(rows))
    print("Books needing normalization:", len(updates))
    print("Updated books:", 0 if dry_run else len(updates))
    print("Dry run:", dry_run)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Normalize books.languages from ISO codes to language names."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report how many rows would change without updating the database."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="PostgreSQL update batch size."
    )

    args = parser.parse_args()

    normalize_book_languages(
        dry_run=args.dry_run,
        batch_size=args.batch_size
    )
