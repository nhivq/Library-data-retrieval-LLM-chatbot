import os
import json
import re
import time
from tqdm import tqdm

from backend.app.scripts.openlibrary.fetch_search import search_books
from backend.app.scripts.openlibrary.fetch_work import fetch_work
from backend.app.scripts.openlibrary.fetch_edition import fetch_editions

from backend.app.scripts.processing.clean_work import clean_work
from backend.app.scripts.processing.clean_edition import clean_edition
from backend.app.scripts.processing.merge_book import merge_book

try:
    from backend.app.scripts.pipeline.config import (
        DEFAULT_SEARCH_LIMIT,
        PROCESSED_KEYS_FILE,
        RAW_WORK_FOLDER,
        CLEAN_FOLDER,
        STATE_FILE
    )
except ModuleNotFoundError:
    from backend.app.scripts.pipeline.config import (
        DEFAULT_SEARCH_LIMIT,
        PROCESSED_KEYS_FILE,
        RAW_WORK_FOLDER,
        CLEAN_FOLDER,
        STATE_FILE
    )


def load_json_file(path, default):

    if not os.path.exists(path):
        return default

    if os.path.getsize(path) == 0:
        return default

    with open(
        path,
        encoding="utf-8"
    ) as f:
        return json.load(f)


def load_processed_keys():

    return set(load_json_file(
        PROCESSED_KEYS_FILE,
        []
    ))


def save_processed_keys(keys):

    with open(
        PROCESSED_KEYS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            list(keys),
            f
        )


def load_state():

    return load_json_file(
        STATE_FILE,
        {
            "last_query": None,
            "last_work_key": None,
            "processed": 0,
            "saved": 0,
            "failed": 0
        }
    )


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


def get_publish_year(edition):

    publish_date = edition.get("publish_date", "")

    match = re.search(r"\d{4}", publish_date)

    if not match:
        return 9999

    return int(match.group())


def select_best_edition(editions):

    entries = editions.get("entries", [])

    if not entries:
        return None

    editions_with_covers = [
        edition
        for edition in entries
        if edition.get("covers")
    ]

    if editions_with_covers:
        # Prefer the earliest covered edition so cover/language fields are useful
        # while the work-level first publish date remains the book date.
        return min(
            editions_with_covers,
            key=get_publish_year
        )

    return min(
        entries,
        key=get_publish_year
    )


def save_clean_book(book):

    filepath = get_clean_book_path(book["work_key"])

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            book,
            f,
            indent=2,
            ensure_ascii=False
        )


def get_clean_book_path(work_key):

    filename = (work_key.split("/")[-1] + ".json")

    return os.path.join(
        CLEAN_FOLDER,
        filename
    )


def run_pipeline(
    query,
    page,
    limit=DEFAULT_SEARCH_LIMIT
):

    print(f"Searching: {query}")

    work_keys = search_books(
        query,
        page,
        limit
    )

    print(f"Found {len(work_keys)} works")

    processed_keys = load_processed_keys()
    saved = 0
    skipped = 0
    failed = 0

    progress = tqdm(
        work_keys,
        total=len(work_keys),
        desc=f"{query} page {page}",
        unit="book"
    )

    for work_key in progress:

        time.sleep(0.2)

        state = load_state()

        state["last_query"] = query
        state["last_work_key"] = work_key

        save_state(state)

        if work_key in processed_keys:

            skipped += 1
            progress.set_postfix(
                saved=saved,
                skipped=skipped,
                failed=failed
            )
            continue

        if os.path.exists(get_clean_book_path(work_key)):

            processed_keys.add(work_key)
            save_processed_keys(processed_keys)

            skipped += 1
            progress.set_postfix(
                saved=saved,
                skipped=skipped,
                failed=failed
            )
            continue

        # 1. fetch work
        try:
            fetch_work(
                work_key
            )

        except Exception as e:
            print(
                "Failed to fetch work:",
                work_key,
                e
            )

            failed += 1
            state = load_state()
            state["failed"] += 1
            save_state(state)

            progress.set_postfix(
                saved=saved,
                skipped=skipped,
                failed=failed
            )
            continue

        work_file = os.path.join(
            RAW_WORK_FOLDER,
            work_key.split("/")[-1] + ".json"
        )

        with open(
            work_file,
            encoding="utf-8"
        ) as f:
            raw_work = json.load(f)

        # 2. fetch editions
        try:
            editions = fetch_editions(work_key)

        except Exception as e:
            print(
                "Failed to fetch editions:",
                work_key,
                e
            )

            editions = {}

        edition = select_best_edition(editions)

        # 3. clean
        clean_w = clean_work(raw_work)
        clean_e = None

        if edition:
            clean_e = clean_edition(edition)

        # 4. merge
        final_book = merge_book(
            clean_w,
            clean_e
        )

        save_clean_book(final_book)

        processed_keys.add(work_key)
        save_processed_keys(processed_keys)

        state = load_state()

        state["saved"] += 1
        state["processed"] += 1

        save_state(state)

        saved += 1
        progress.set_postfix(
            saved=saved,
            skipped=skipped,
            failed=failed
        )

    return {
        "saved": saved,
        "skipped": skipped,
        "failed": failed,
        "total": len(work_keys)
    }


if __name__ == "__main__":
    run_pipeline(
        "fantasy",
        page=1
    )
