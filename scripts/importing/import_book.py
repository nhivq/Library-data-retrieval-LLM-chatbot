# Logic: for book: if exists -> UPDATE; else -> INSERT

import os
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database.connection import get_connection
from scripts.importing.config import BATCH_SIZE, DRY_RUN
from scripts.processing.language_names import normalize_languages


CLEAN_BOOK_FOLDER = f"{PROJECT_ROOT}/data/clean/works"

STATE_FILE = f"{PROJECT_ROOT}/scripts/logs/import_state.json"

FAILED_FILE = f"{PROJECT_ROOT}/scripts/logs/failed_books.json"


def load_state():

    with open(
        STATE_FILE,
        encoding="utf-8"
    ) as f:
        return json.load(f)


def save_state(state):

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            state,
            f,
            indent=4
        )


def save_failed(book, error):

    failed = []

    if os.path.exists(FAILED_FILE):

        with open(
            FAILED_FILE,
            encoding="utf-8"
        ) as f:
            failed = json.load(f)

    failed.append(
        {
            "work_key": book.get("work_key"),
            "title": book.get("title"),
            "error": str(error)
        }
    )

    with open(
        FAILED_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            failed,
            f,
            indent=4
        )


def is_valid_book(book):

    if not book.get("cover_id") and not book.get("description"):
        return False

    return True


def import_books():

    conn = get_connection()
    cursor = conn.cursor()

    files = sorted ([
        f for f in os.listdir(
            CLEAN_BOOK_FOLDER
        )
        if f.endswith(".json")
    ])

    total = len(files)

    processed = 0
    imported = 0
    skipped = 0
    failed = 0
    updated = 0
    new = 0
    batch = 0

    state = load_state()

    last_file = state.get("last_file")

    last_processed_file = None

    for filename in files:

        # Resume from the last committed file. Keep filenames stable and sorted.
        if last_file:

            if filename <= last_file:
                continue

        last_processed_file = filename

        filepath = os.path.join(
            CLEAN_BOOK_FOLDER,
            filename
        )

        with open(
            filepath,
            encoding="utf-8"
        ) as f:

            book = json.load(f)

        book["languages"] = normalize_languages(
            book.get("languages", [])
        )

        processed += 1

        if not is_valid_book(book):

            skipped += 1
            continue

        try:

            if DRY_RUN:

                imported += 1
                continue

            # Let PostgreSQL's PRIMARY KEY/UNIQUE index decide insert vs update.
            # This avoids an extra SELECT per book during large imports.
            cursor.execute(
                """
                INSERT INTO books
                (
                    work_key,
                    title,
                    tags,
                    publish_date,
                    description,
                    languages,
                    publishers,
                    cover_id,
                )

                VALUES
                (
                    %(work_key)s,
                    %(title)s,
                    %(tags)s,
                    %(publish_date)s,
                    %(description)s,
                    %(languages)s,
                    %(publishers)s,
                    %(cover_id)s
                )

                ON CONFLICT(work_key)

                DO UPDATE SET
                    title = EXCLUDED.title,
                    tags = EXCLUDED.tags,
                    publish_date = EXCLUDED.publish_date,
                    description = EXCLUDED.description,
                    languages = EXCLUDED.languages,
                    publishers = EXCLUDED.publishers,
                    cover_id = EXCLUDED.cover_id

                RETURNING (xmax = 0) AS inserted
                """,
                book
            )

            inserted = cursor.fetchone()[0]

            if inserted:
                new += 1

            else:
                updated += 1

            imported += 1

        except Exception as e:

            failed += 1

            save_failed(book, e)

            conn.rollback()

            continue

        if imported % BATCH_SIZE == 0:

            conn.commit()

            state["last_file"] = filename
            state["processed"] = processed
            state["imported"] = imported
            state["skipped"] = skipped
            state["failed"] = failed
            state["new"] = new
            state["updated"] = updated

            save_state(state)

            batch += 1

            print(
                f"""
                Batch {batch}
                Processed: {processed}
                Imported: {imported}
                Skipped: {skipped}
                New: {new}
                Updated: {updated}
                """
            )

    conn.commit()

    if last_processed_file is None:
        print("No new clean book files found")
        cursor.close()
        conn.close()
        return

    state["last_file"] = last_processed_file
    state["processed"] = processed
    state["imported"] = imported
    state["skipped"] = skipped
    state["failed"] = failed
    state["new"] = new
    state["updated"] = updated

    save_state(state)

    cursor.close()
    conn.close()

    print("Finished")
    print(f"Processed: {processed}")
    print(f"Imported: {imported}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"New books: {new}")
    print(f"Updated books: {updated}")
    print(f"Dry run: {DRY_RUN}")


if __name__ == "__main__":
    import_books()
