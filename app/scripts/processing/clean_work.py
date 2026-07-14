from datetime import datetime

from app.scripts.processing.language_names import normalize_languages


def get_cover(raw):

    covers = raw.get("covers") or []

    if not covers:
        return None

    cover = covers[0]

    if cover == -1:
        return None

    return cover


def clean_description(raw):

    description = raw.get("description")

    if not description:
        return None

    if isinstance(
        description,
        str
    ):
        return description

    if isinstance(
        description,
        dict
    ):
        return description.get("value")

    return None


def get_publish_date(raw):

    date = raw.get("first_publish_date")

    if not date:
        return None

    try:
        # Store a JSON-safe value that PostgreSQL can still cast into DATE.
        return datetime.strptime(date, "%Y").date().isoformat()

    except ValueError:
        return None
    

def get_authors(raw):

    authors = []

    for item in raw.get("authors", []):

        author = item.get("author", {})

        key = author.get("key")

        if key:
            authors.append(key)

    return authors


def clean_work(raw):

    return {

        "work_key":
        raw.get("key"),

        "title":
        raw.get("title"),

        "description":
        clean_description(raw),

        "publish_date":
        get_publish_date(raw),

        "cover_id":
        get_cover(raw),

        # OpenLibrary calls these "subjects"; this project stores them as "tags".
        "tags":
        raw.get("subjects", []),

        "languages":
        normalize_languages(
            raw.get("languages") or raw.get("language") or []
        ),

        "authors":
        get_authors(raw)

    }
