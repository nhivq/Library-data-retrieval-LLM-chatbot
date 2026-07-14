import os
import json
from pathlib import Path
import sys
import argparse

from psycopg2.extras import Json

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database.connection import get_connection


CLEAN_AUTHOR_FOLDER = f"{PROJECT_ROOT}/data/clean/authors"
BATCH_SIZE = 1000

AUTHOR_FIELDS = {
    "author_name": "author_name",
    "fuller_name": "fuller_name",
    "alternate_names": "alternate_names",
    "birth_date": "birth_date",
    "death_date": "death_date",
    "bio": "bio",
    "photo_id": "photo_id",
    "photo": "photo_id",
    "cover_image": "photo_id",
    "cover": "photo_id",
    "links": "links",
    "openlibrary_updated_at": "openlibrary_updated_at",
}


def normalize_fields(fields):

    if not fields:
        return None

    normalized = []

    for field in fields:
        column = AUTHOR_FIELDS[field]

        if column not in normalized:
            normalized.append(column)

    return normalized


def prepare_author(author):

    author["links"] = Json(author.get("links", []))

    return author


def build_import_query(fields):

    if fields is None:
        fields = [
            "author_name",
            "fuller_name",
            "alternate_names",
            "birth_date",
            "death_date",
            "bio",
            "photo_id",
            "links",
            "openlibrary_updated_at",
        ]

    insert_columns = [
        "author_key",
        "author_name",
    ]

    for field in fields:
        if field not in insert_columns:
            insert_columns.append(field)

    placeholders = [
        f"%({column})s"
        for column in insert_columns
    ]

    update_columns = [
        field
        for field in fields
        if field != "author_key"
    ]

    update_assignments = [
        f"{column} = EXCLUDED.{column}"
        for column in update_columns
    ]

    return f"""
        INSERT INTO authors
        (
            {", ".join(insert_columns)}
        )

        VALUES
        (
            {", ".join(placeholders)}
        )

        ON CONFLICT(author_key)

        DO UPDATE SET

            {", ".join(update_assignments)}
        """


def import_authors(fields=None, batch_size=BATCH_SIZE):

    conn = get_connection()
    cursor = conn.cursor()

    imported = 0
    fields = normalize_fields(fields)
    query = build_import_query(fields)

    for filename in sorted(os.listdir(CLEAN_AUTHOR_FOLDER)):

        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(
            CLEAN_AUTHOR_FOLDER,
            filename
        )

        with open(
            filepath,
            encoding="utf-8"
        ) as f:

            author = json.load(f)

        author = prepare_author(author)

        cursor.execute(
            query,
            author
        )

        imported += 1

        if imported % batch_size == 0:
            conn.commit()
            print(f"Imported {imported} authors")

    conn.commit()

    cursor.close()
    conn.close()

    print(f"Imported {imported} authors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import cleaned author data into PostgreSQL."
    )

    parser.add_argument(
        "--field",
        "--fields",
        nargs="+",
        choices=sorted(AUTHOR_FIELDS),
        help=(
            "Only import/update these author fields. "
            "Use photo_id, photo, cover, or cover_image for author images."
        )
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="Commit after this many authors."
    )

    args = parser.parse_args()

    import_authors(
        fields=args.field,
        batch_size=args.batch_size
    )
