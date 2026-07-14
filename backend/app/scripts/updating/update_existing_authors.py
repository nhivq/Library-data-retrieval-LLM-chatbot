import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
from pathlib import Path
import sys

import requests
from psycopg2.extras import Json, execute_batch
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.connection import get_connection
from backend.app.scripts.importing.import_author import AUTHOR_FIELDS, normalize_fields
from backend.app.scripts.openlibrary.client import get
from backend.app.scripts.processing.clean_author import clean_author


BATCH_SIZE = 1000
SLEEP_TIME = 0.1
WORKERS = 4
STATE_FILE = PROJECT_ROOT / "scripts" / "logs" / "update_authors_state.json"
RAW_AUTHOR_FOLDER = PROJECT_ROOT / "data" / "raw" / "authors"
CLEAN_AUTHOR_FOLDER = PROJECT_ROOT / "data" / "clean" / "authors"


def new_state(fields):

    return {
        "fields": fields,
        "last_author_key": None,
        "processed": 0,
        "updated": 0,
        "missing": 0,
        "failed": 0,
    }


def load_state(fields):

    if not STATE_FILE.exists() or STATE_FILE.stat().st_size == 0:
        return new_state(fields)

    with open(
        STATE_FILE,
        encoding="utf-8"
    ) as f:
        state = json.load(f)

    if state.get("fields") != fields:
        return new_state(fields)

    return state


def save_state(state):

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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


def reset_state(fields):

    save_state(
        new_state(fields)
    )


def fetch_author(author_key):

    try:
        return get(f"{author_key}.json")

    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None

        raise


def save_author_files(author):

    author_id = author["author_key"].split("/")[-1]

    RAW_AUTHOR_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )
    CLEAN_AUTHOR_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    raw_path = RAW_AUTHOR_FOLDER / f"{author_id}.json"
    clean_path = CLEAN_AUTHOR_FOLDER / f"{author_id}.json"

    with open(
        raw_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            author["raw"],
            f,
            indent=2,
            ensure_ascii=False
        )

    with open(
        clean_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            author["clean"],
            f,
            indent=2,
            ensure_ascii=False
        )


def chunked(items, size):

    for index in range(0, len(items), size):
        yield items[index:index + size]


def build_missing_filter(fields):

    if not fields:
        return ""

    checks = [
        f"{field} IS NULL"
        for field in fields
    ]

    return f"WHERE {' OR '.join(checks)}"


def fetch_author_keys(cursor, fields=None, only_missing=False):

    missing_filter = ""

    if only_missing:
        missing_filter = build_missing_filter(fields)

    cursor.execute(
        f"""
        SELECT author_key
        FROM authors
        {missing_filter}
        ORDER BY author_key
        """
    )

    return [
        row[0]
        for row in cursor.fetchall()
    ]


def build_update_query(fields, keep_existing_nulls=True):

    if keep_existing_nulls:
        assignments = [
            f"{field} = COALESCE(%({field})s, {field})"
            for field in fields
        ]

    else:
        assignments = [
            f"{field} = %({field})s"
            for field in fields
        ]

    return f"""
        UPDATE authors
        SET {", ".join(assignments)}
        WHERE author_key = %(author_key)s
        """


def prepare_author(author):

    author["links"] = Json(author.get("links", []))

    return author


def fetch_clean_author(author_key, save_files=True, sleep_time=SLEEP_TIME):

    try:
        raw_author = fetch_author(author_key)

        if not raw_author:
            return {
                "status": "missing",
                "author_key": author_key,
            }

        clean = clean_author(raw_author)
        db_author = prepare_author(clean.copy())

        if save_files:
            save_author_files(
                {
                    "author_key": author_key,
                    "raw": raw_author,
                    "clean": clean,
                }
            )

        return {
            "status": "updated",
            "author_key": author_key,
            "author": db_author,
        }

    except Exception as e:
        return {
            "status": "failed",
            "author_key": author_key,
            "error": e,
        }

    finally:
        if sleep_time:
            time.sleep(sleep_time)


def process_author_batch(author_keys, workers, save_files, sleep_time, progress):

    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                fetch_clean_author,
                author_key,
                save_files,
                sleep_time
            )
            for author_key in author_keys
        ]

        for future in as_completed(futures):
            results.append(future.result())
            progress.update(1)

    return results


def update_existing_authors(
    fields,
    batch_size=BATCH_SIZE,
    sleep_time=SLEEP_TIME,
    workers=WORKERS,
    only_missing=False,
    reset=False,
    save_files=True,
    overwrite_nulls=False
):

    fields = normalize_fields(fields)

    if not fields:
        raise ValueError("Choose at least one --field for DB author updates.")

    if reset:
        reset_state(fields)

    state = load_state(fields)

    conn = get_connection()
    cursor = conn.cursor()

    author_keys = fetch_author_keys(
        cursor,
        fields=fields,
        only_missing=only_missing
    )
    update_query = build_update_query(
        fields,
        keep_existing_nulls=not overwrite_nulls
    )
    author_keys = [
        author_key
        for author_key in author_keys
        if (
            not state.get("last_author_key")
            or author_key > state["last_author_key"]
        )
    ]

    updated = 0
    missing = 0
    failed = 0

    progress = tqdm(
        total=len(author_keys),
        desc="Updating authors",
        unit="author"
    )

    for batch_author_keys in chunked(author_keys, batch_size):
        results = process_author_batch(
            batch_author_keys,
            workers=workers,
            save_files=save_files,
            sleep_time=sleep_time,
            progress=progress
        )

        authors_to_update = [
            result["author"]
            for result in results
            if result["status"] == "updated"
        ]

        if authors_to_update:
            execute_batch(
                cursor,
                update_query,
                authors_to_update,
                page_size=batch_size
            )

        for result in results:
            if result["status"] == "updated":
                updated += 1
                state["updated"] += 1

            elif result["status"] == "missing":
                missing += 1
                state["missing"] += 1

            else:
                failed += 1
                state["failed"] += 1
                print(
                    "Failed:",
                    result["author_key"],
                    result["error"]
                )

        state["processed"] += len(batch_author_keys)
        state["last_author_key"] = batch_author_keys[-1]

        save_state(state)
        conn.commit()

        progress.set_postfix(
            updated=updated,
            missing=missing,
            failed=failed
        )

    progress.close()
    conn.commit()

    cursor.close()
    conn.close()

    print("Finished")
    print("Updated:", updated)
    print("Missing:", missing)
    print("Failed:", failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch OpenLibrary data for authors already in the DB."
    )

    parser.add_argument(
        "--field",
        "--fields",
        nargs="+",
        required=True,
        choices=sorted(AUTHOR_FIELDS),
        help=(
            "Author DB fields to update. "
            "Use photo_id, photo, cover, or cover_image for author images."
        )
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="Commit after this many updated authors."
    )

    parser.add_argument(
        "--sleep",
        type=float,
        default=SLEEP_TIME,
        help="Seconds to sleep between OpenLibrary requests."
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=WORKERS,
        help="Number of concurrent OpenLibrary fetches."
    )

    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Only fetch authors where at least one selected field is NULL."
    )

    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Start from the first selected author instead of resuming."
    )

    parser.add_argument(
        "--no-save-files",
        action="store_true",
        help="Do not save fetched raw/clean author JSON files."
    )

    parser.add_argument(
        "--overwrite-nulls",
        action="store_true",
        help="Allow missing OpenLibrary values to overwrite existing DB values."
    )

    args = parser.parse_args()

    update_existing_authors(
        fields=args.field,
        batch_size=args.batch_size,
        sleep_time=args.sleep,
        workers=args.workers,
        only_missing=args.only_missing,
        reset=args.reset_state,
        save_files=not args.no_save_files,
        overwrite_nulls=args.overwrite_nulls
    )
