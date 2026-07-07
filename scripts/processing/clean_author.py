def clean_links(raw_links):

    if not raw_links:
        return []

    cleaned = []

    for link in raw_links:

        url = link.get("url")

        if not url:
            continue

        cleaned.append(
            {
                "title": link.get("title"),
                "url": link.get("url")
            }
        )

    return cleaned


def clean_bio(raw):

    bio = raw.get("bio")

    if not bio:
        return None

    if isinstance(bio, dict):
        return bio.get("value")

    return bio


def get_photo(raw):

    photos = raw.get(
        "photos",
        []
    )

    if len(photos) == 0:
        return None

    photo = photos[0]

    if photos[0] == -1:
        return None

    return photo


def clean_datetime(raw):

    modified = raw.get("last_modified")

    if not modified:
        return None

    return modified.get("value")


def clean_author(raw):

    return {
        "author_key":
        raw.get("key"),

        "author_name":
        raw.get("name"),

        "fuller_name":
        raw.get("fuller_name"),

        "alternate_names":
        raw.get("alternate_names", []),

        "birth_date":
        raw.get("birth_date"),

        "death_date":
        raw.get("death_date"),

        "bio":
        clean_bio(raw),

        "photo_id":
        get_photo(raw),

        "links":
        clean_links(
            raw.get("links")
        ),

        "openlibrary_updated_at":
        clean_datetime(raw)
    }