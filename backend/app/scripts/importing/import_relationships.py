import os
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.connection import get_connection


CLEAN_BOOK_FOLDER = f"{PROJECT_ROOT}/data/clean/works"


def import_relationships():

    conn = get_connection()
    cursor = conn.cursor()

    imported = 0

    for filename in os.listdir(
        CLEAN_BOOK_FOLDER
    ):

        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(
            CLEAN_BOOK_FOLDER,
            filename
        )

        with open(
            filepath,
            encoding="utf-8"
        ) as f:

            book = json.load(f)

        work_key = book.get("work_key")

        authors = book.get("authors", [])

        # skip books with no author info
        if not authors:
            continue

        for author_key in authors:

            cursor.execute(
                """
                INSERT INTO book_authors
                (
                    work_key,
                    author_key
                )

                VALUES
                (%s, %s)

                ON CONFLICT
                DO NOTHING
                """,

                (
                    work_key,
                    author_key
                )
            )

            imported += 1

    conn.commit()

    cursor.close()
    conn.close()

    print(f"Imported {imported} relationships")


if __name__ == "__main__":
    import_relationships()
