import argparse
import gzip
import json
from pathlib import Path
import sys

from psycopg2.extras import execute_batch
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.connection import get_connection
from backend.app.scripts.processing.clean_edition import clean_edition


DEFAULT_DUMP_FILE = PROJECT_ROOT / "db_source" / "ol_dump_editions_2026-05-31.txt.gz"
BATCH_SIZE = 1000

BOOK_FIELDS = {
    "cover_id",
    "publish_date",
    "languages",
    "publishers",
}


def normalize_fields(fields):

    if not fields:
        return [
            "cover_id",
            "publish_date",
            "languages",
            "publishers",
        ]

    return list(dict.fromkeys(fields))


def build_missing_filter(fields):

    checks = []

    for field in fields:
        if field in ("languages", "publishers"):
            checks.append(f"({field} IS NULL OR cardinality({field}) = 0)")
        else:
            checks.append(f"{field} IS NULL")

    return " OR ".join(checks)


def fetch_target_work_keys(cursor, fields, only_missing):

    where_clause = ""

    if only_missing:
        where_clause = f"WHERE {build_missing_filter(fields)}"

    cursor.execute(
        f"""
        SELECT work_key
        FROM books
        {where_clause}
        """
    )

    return {
        row[0]
        for row in cursor.fetchall()
    }


def get_work_keys(raw_edition):

    work_keys = []

    for work in raw_edition.get("works", []):
        key = work.get("key")

        if key:
            work_keys.append(key)

    return work_keys


def has_selected_value(edition, fields):

    for field in fields:
        value = edition.get(field)

        if isinstance(value, list) and value:
            return True

        if value is not None and not isinstance(value, list):
            return True

    return False


def edition_score(edition, fields):

    score = 0

    for field in fields:
        value = edition.get(field)

        if isinstance(value, list) and value:
            score += 1

        elif value is not None and not isinstance(value, list):
            score += 1

    if edition.get("cover_id"):
        score += 3

    if edition.get("publish_date"):
        score += 1

    return score


def is_better_edition(candidate, current, fields):

    if current is None:
        return True

    candidate_score = edition_score(candidate, fields)
    current_score = edition_score(current, fields)

    if candidate_score != current_score:
        return candidate_score > current_score

    candidate_date = candidate.get("publish_date") or "9999-01-01"
    current_date = current.get("publish_date") or "9999-01-01"

    return candidate_date < current_date


def parse_dump_line(line):

    parts = line.rstrip("\n").split("\t", 4)

    if len(parts) < 5:
        return None

    return json.loads(parts[4])


def scan_edition_dump(dump_file, target_work_keys, fields, limit_lines=None):

    best_by_work = {}
    scanned = 0
    matched = 0

    with gzip.open(
        dump_file,
        "rt",
        encoding="utf-8"
    ) as f:
        progress = tqdm(
            f,
            desc="Scanning edition dump",
            unit="edition"
        )

        for line in progress:
            scanned += 1

            if limit_lines and scanned > limit_lines:
                break

            try:
                raw_edition = parse_dump_line(line)

            except json.JSONDecodeError:
                continue

            if not raw_edition:
                continue

            matching_work_keys = [
                work_key
                for work_key in get_work_keys(raw_edition)
                if work_key in target_work_keys
            ]

            if not matching_work_keys:
                continue

            cleaned = clean_edition(raw_edition)

            if not has_selected_value(cleaned, fields):
                continue

            for work_key in matching_work_keys:
                current = best_by_work.get(work_key)

                if is_better_edition(
                    cleaned,
                    current,
                    fields
                ):
                    best_by_work[work_key] = {
                        "work_key": work_key,
                        **cleaned,
                    }
                    matched += 1

            if scanned % 10000 == 0:
                progress.set_postfix(
                    matched=len(best_by_work)
                )

    return {
        "scanned": scanned,
        "matched": matched,
        "books": list(best_by_work.values()),
    }


def build_update_query(fields, overwrite=False):

    if overwrite:
        assignments = [
            f"{field} = %({field})s"
            for field in fields
        ]

    else:
        assignments = []

        for field in fields:
            if field in ("languages", "publishers"):
                assignments.append(
                    f"{field} = COALESCE(NULLIF(%({field})s, ARRAY[]::text[]), {field})"
                )
            else:
                assignments.append(
                    f"{field} = COALESCE(%({field})s, {field})"
                )

    return f"""
        UPDATE books
        SET {", ".join(assignments)}
        WHERE work_key = %(work_key)s
        """


def update_books(cursor, books, fields, batch_size, overwrite):

    if not books:
        return 0

    query = build_update_query(
        fields,
        overwrite=overwrite
    )

    execute_batch(
        cursor,
        query,
        books,
        page_size=batch_size
    )

    return len(books)


def run_update(
    dump_file,
    fields,
    only_missing=True,
    batch_size=BATCH_SIZE,
    overwrite=False,
    limit_lines=None,
    dry_run=False
):

    fields = normalize_fields(fields)

    conn = get_connection()
    cursor = conn.cursor()

    target_work_keys = fetch_target_work_keys(
        cursor,
        fields=fields,
        only_missing=only_missing
    )

    print(f"Target books: {len(target_work_keys)}")

    result = scan_edition_dump(
        dump_file=dump_file,
        target_work_keys=target_work_keys,
        fields=fields,
        limit_lines=limit_lines
    )

    if dry_run:
        updated = 0

    else:
        updated = update_books(
            cursor,
            books=result["books"],
            fields=fields,
            batch_size=batch_size,
            overwrite=overwrite
        )

    if dry_run:
        conn.rollback()

    else:
        conn.commit()
    cursor.close()
    conn.close()

    print("Finished")
    print("Scanned editions:", result["scanned"])
    print("Matched books:", len(result["books"]))
    print("Updated books:", updated)

    if dry_run:
        print("Dry run: no database rows were updated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update existing books from a local OpenLibrary editions dump."
    )

    parser.add_argument(
        "--dump-file",
        type=Path,
        default=DEFAULT_DUMP_FILE,
        help="Path to ol_dump_editions_*.txt.gz."
    )

    parser.add_argument(
        "--field",
        "--fields",
        nargs="+",
        choices=sorted(BOOK_FIELDS),
        help="Book fields to update from edition data."
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="PostgreSQL update batch size."
    )

    parser.add_argument(
        "--all-books",
        action="store_true",
        help="Scan for all existing books, not only books missing selected fields."
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing DB values instead of only filling NULL values."
    )

    parser.add_argument(
        "--limit-lines",
        type=int,
        help="Debug option: scan only this many dump lines."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report matches without updating the database."
    )

    args = parser.parse_args()

    run_update(
        dump_file=args.dump_file,
        fields=args.field,
        only_missing=not args.all_books,
        batch_size=args.batch_size,
        overwrite=args.overwrite,
        limit_lines=args.limit_lines,
        dry_run=args.dry_run
    )
