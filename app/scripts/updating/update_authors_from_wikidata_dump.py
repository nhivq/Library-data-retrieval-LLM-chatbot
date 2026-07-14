import argparse
import csv
import gzip
import json
import sys as system
from pathlib import Path
import sys

from psycopg2.extras import Json, execute_batch
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database.connection import get_connection


DEFAULT_DUMP_FILE = PROJECT_ROOT / "db_source" / "ol_dump_wikidata_2026-05-31.txt.gz"
BATCH_SIZE = 1000

csv.field_size_limit(system.maxsize)

AUTHOR_FIELDS = [
    "fuller_name",
    "alternate_names",
    "birth_date",
    "death_date",
    "bio",
    "links",
]


def get_statement_values(item, property_id):
    statements = item.get("statements", {})
    values = []

    for statement in statements.get(property_id, []):
        value = statement.get("value", {})

        if value.get("type") != "value":
            continue

        content = value.get("content")

        if content is not None:
            values.append(content)

    return values


def first_statement_value(item, property_id):
    values = get_statement_values(item, property_id)

    if not values:
        return None

    return values[0]


def normalize_wikidata_time(value):
    if not isinstance(value, dict):
        return None

    raw_time = value.get("time")

    if not raw_time:
        return None

    # Wikidata times look like +1854-09-11T00:00:00Z.
    return raw_time.lstrip("+").split("T", 1)[0]


def get_english_value(mapping):
    if not mapping:
        return None

    return mapping.get("en")


def build_links(item):
    links = []
    wikidata_id = item.get("id")

    if wikidata_id:
        links.append(
            {
                "title": "Wikidata",
                "url": f"https://www.wikidata.org/wiki/{wikidata_id}",
            }
        )

    viaf_id = first_statement_value(item, "P214")

    if viaf_id:
        links.append(
            {
                "title": "VIAF",
                "url": f"https://viaf.org/viaf/{viaf_id}",
            }
        )

    isni_id = first_statement_value(item, "P213")

    if isni_id:
        links.append(
            {
                "title": "ISNI",
                "url": f"https://isni.org/isni/{isni_id}",
            }
        )

    loc_id = first_statement_value(item, "P244")

    if loc_id:
        links.append(
            {
                "title": "Library of Congress",
                "url": f"https://id.loc.gov/authorities/names/{loc_id}",
            }
        )

    commons_image = first_statement_value(item, "P18")

    if commons_image:
        links.append(
            {
                "title": "Wikimedia Commons image",
                "url": (
                    "https://commons.wikimedia.org/wiki/Special:FilePath/"
                    f"{commons_image}"
                ),
            }
        )

    return links


def build_author_record(item, author_key):
    labels = item.get("labels", {})
    descriptions = item.get("descriptions", {})
    aliases = item.get("aliases", {})

    alternate_names = aliases.get("en", [])

    return {
        "author_key": author_key,
        "fuller_name": get_english_value(labels),
        "alternate_names": alternate_names,
        "birth_date": normalize_wikidata_time(
            first_statement_value(item, "P569")
        ),
        "death_date": normalize_wikidata_time(
            first_statement_value(item, "P570")
        ),
        "bio": get_english_value(descriptions),
        "links": Json(build_links(item)),
    }


def parse_dump_row(row):
    if len(row) < 2:
        return None

    try:
        return json.loads(row[1])

    except json.JSONDecodeError:
        return None


def extract_openlibrary_author_keys(item):
    keys = []

    for openlibrary_id in get_statement_values(item, "P648"):
        if not isinstance(openlibrary_id, str):
            continue

        if not openlibrary_id.startswith("OL"):
            continue

        keys.append(f"/authors/{openlibrary_id}")

    return keys


def build_missing_filter(fields):
    checks = []

    for field in fields:
        if field == "alternate_names":
            checks.append(f"({field} IS NULL OR cardinality({field}) = 0)")
        elif field == "links":
            checks.append(f"({field} IS NULL OR {field} = '[]'::jsonb)")
        else:
            checks.append(f"({field} IS NULL OR BTRIM({field}) = '')")

    return " OR ".join(checks)


def fetch_target_author_keys(cursor, fields, only_missing):
    where_clause = ""

    if only_missing:
        where_clause = f"WHERE {build_missing_filter(fields)}"

    cursor.execute(
        f"""
        SELECT author_key
        FROM authors
        {where_clause}
        """
    )

    return {
        row[0]
        for row in cursor.fetchall()
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
            if field == "alternate_names":
                assignments.append(
                    f"{field} = COALESCE(NULLIF(%({field})s, ARRAY[]::text[]), {field})"
                )
            elif field == "links":
                assignments.append(
                    f"{field} = COALESCE(NULLIF(%({field})s, '[]'::jsonb), {field})"
                )
            else:
                assignments.append(
                    f"{field} = COALESCE(NULLIF(%({field})s, ''), {field})"
                )

    return f"""
        UPDATE authors
        SET {", ".join(assignments)}
        WHERE author_key = %(author_key)s
        """


def scan_wikidata_dump(dump_file, target_author_keys, limit_lines=None):
    updates_by_author = {}
    scanned = 0
    matched = 0
    candidate_rows = 0

    with gzip.open(
        dump_file,
        "rt",
        encoding="utf-8",
        newline=""
    ) as f:
        progress = tqdm(
            f,
            desc="Scanning Wikidata dump",
            unit="item"
        )

        for line in progress:
            scanned += 1

            if limit_lines and scanned > limit_lines:
                break

            if '""P648""' not in line and '"P648"' not in line:
                continue

            candidate_rows += 1

            try:
                row = next(
                    csv.reader(
                        [line],
                        delimiter="\t",
                        quotechar='"'
                    )
                )

            except csv.Error:
                continue

            item = parse_dump_row(row)

            if not item:
                continue

            matching_author_keys = [
                author_key
                for author_key in extract_openlibrary_author_keys(item)
                if author_key in target_author_keys
            ]

            if not matching_author_keys:
                continue

            matched += 1

            for author_key in matching_author_keys:
                updates_by_author[author_key] = build_author_record(
                    item,
                    author_key
                )

            if scanned % 10000 == 0:
                progress.set_postfix(
                    candidates=candidate_rows,
                    matched=len(updates_by_author)
                )

    return {
        "scanned": scanned,
        "candidate_rows": candidate_rows,
        "matched_items": matched,
        "authors": list(updates_by_author.values()),
    }


def update_authors(cursor, authors, fields, batch_size, overwrite):
    if not authors:
        return 0

    execute_batch(
        cursor,
        build_update_query(
            fields,
            overwrite=overwrite
        ),
        authors,
        page_size=batch_size
    )

    return len(authors)


def run_update(
    dump_file,
    fields,
    only_missing=True,
    batch_size=BATCH_SIZE,
    overwrite=False,
    limit_lines=None,
    dry_run=False
):
    conn = get_connection()
    cursor = conn.cursor()

    target_author_keys = fetch_target_author_keys(
        cursor,
        fields=fields,
        only_missing=only_missing
    )

    print(f"Target authors: {len(target_author_keys)}")

    result = scan_wikidata_dump(
        dump_file=dump_file,
        target_author_keys=target_author_keys,
        limit_lines=limit_lines
    )

    if dry_run:
        updated = 0
        conn.rollback()

    else:
        updated = update_authors(
            cursor,
            authors=result["authors"],
            fields=fields,
            batch_size=batch_size,
            overwrite=overwrite
        )
        conn.commit()

    cursor.close()
    conn.close()

    print("Finished")
    print("Scanned Wikidata items:", result["scanned"])
    print("Rows with Open Library author IDs:", result["candidate_rows"])
    print("Matched Wikidata items:", result["matched_items"])
    print("Matched authors:", len(result["authors"]))
    print("Updated authors:", updated)

    if dry_run:
        print("Dry run: no database rows were updated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update existing authors from a local OpenLibrary Wikidata dump."
    )

    parser.add_argument(
        "--dump-file",
        type=Path,
        default=DEFAULT_DUMP_FILE,
        help="Path to ol_dump_wikidata_*.txt.gz."
    )

    parser.add_argument(
        "--field",
        "--fields",
        nargs="+",
        choices=AUTHOR_FIELDS,
        default=AUTHOR_FIELDS,
        help="Author fields to update from Wikidata."
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="PostgreSQL update batch size."
    )

    parser.add_argument(
        "--all-authors",
        action="store_true",
        help="Scan for all existing authors, not only authors missing selected fields."
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing DB values instead of only filling missing values."
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
        only_missing=not args.all_authors,
        batch_size=args.batch_size,
        overwrite=args.overwrite,
        limit_lines=args.limit_lines,
        dry_run=args.dry_run
    )
