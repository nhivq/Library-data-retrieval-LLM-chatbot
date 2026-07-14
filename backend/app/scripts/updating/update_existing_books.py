import time
import json
from pathlib import Path
import sys
from tqdm import tqdm
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(
    0,
    str(PROJECT_ROOT)
)

from backend.app.database.connection import get_connection
from backend.app.scripts.openlibrary.client import get
from backend.app.scripts.processing.clean_work import clean_work


BATCH_SIZE = 1000
SLEEP_TIME = 0.1

STATE_FILE = (f"{PROJECT_ROOT}/scripts/logs/update_state.json")


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


def fetch_work(work_key):

    try:
        return get(f"{work_key}.json")

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None

        raise


# Create update function
def update_book(
    cursor,
    book
):

    cursor.execute(
        """
        UPDATE books

        SET

        title = %(title)s,
        tags = %(tags)s,
        description = COALESCE(
            %(description)s,
            description
        ),

        cover_id = COALESCE(
            %(cover_id)s,
            cover_id
        ),
        languages = %(languages)s

        WHERE work_key = %(work_key)s
        """,
        book
    )


# Main update loop
def update_existing_books():

    state = load_state()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            work_key,
            cover_id,
            description
        FROM books
        WHERE cover_id IS NULL
           OR description IS NULL
        ORDER BY work_key
        """
    )

    books = cursor.fetchall()

    updated = 0
    missing = 0
    failed = 0

    for index, row in enumerate(
        tqdm(books,
        total=len(books),
        desc="Updating books")
    ):

        work_key = row[0]
        current_cover = row[1]

        if (
            state.get("last_work_key")
            and
            work_key <= state.get("last_work_key")
            and 
            current_cover
        ):
            continue

        try:

            raw = fetch_work(work_key)

            if not raw:
                missing += 1
                state["missing"] = missing
                state["processed"] += 1
                state["last_work_key"] = work_key

                save_state(state)

                continue

            cleaned = clean_work(raw)

            update_book(
                cursor,
                cleaned
            )

            updated += 1
            state["last_work_key"] = work_key
            state["processed"] += 1
            state["updated"] = updated

            save_state(state)

            if updated % BATCH_SIZE == 0:
                conn.commit()

                print(
                    f"""
                    Batch update
                    Processed: {index + 1}
                    Updated: {updated}
                    Missing: {missing}
                    Failed: {failed}
                    """
                    )

            time.sleep(SLEEP_TIME)

        except Exception as e:

            failed += 1
            state["failed"] = failed
            state["processed"] += 1
            state["last_work_key"] = work_key

            save_state(state)

            print(
                "Failed:",
                work_key,
                e
            )

    conn.commit()

    cursor.close()
    conn.close()

    print("Finished")
    print("Updated:", updated)
    print("Missing:", missing)
    print("Failed:", failed)


if __name__ == "__main__":
    update_existing_books()
