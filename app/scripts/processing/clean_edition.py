import re

from app.scripts.processing.language_names import normalize_languages


def get_cover(raw):

    covers = raw.get("covers", [])

    if not covers:
        return None

    cover = covers[0]

    if cover == -1:
        return None

    return cover


def clean_languages(raw):

    return normalize_languages(
        raw.get("languages", [])
    )


def clean_publish_date(raw):

    publish_date = raw.get("publish_date")

    if not publish_date:
        return None

    match = re.search(r"\d{4}", publish_date)

    if not match:
        return None

    year = int(match.group())

    if year < 1:
        return None

    # Edition dates are often free text; keep the book import date PostgreSQL-safe.
    return f"{year:04d}-01-01"


def clean_edition(raw):

    return {

        "cover_id":
            get_cover(raw),

        "publish_date":
            clean_publish_date(raw),

        "languages":
            clean_languages(raw),

        "publishers":
            raw.get("publishers", [])
    }
