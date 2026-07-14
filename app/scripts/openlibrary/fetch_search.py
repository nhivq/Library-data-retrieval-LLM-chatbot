# Search API layer to get candidates

try:
    from app.scripts.openlibrary.client import get
except ModuleNotFoundError:
    from app.scripts.openlibrary.client import get


def search_books(
    query,
    page=1,
    limit=1000
):

    data = get(
        "search.json",
        params={
            "q": query,
            "page": page,
            "limit": limit
        }
    )

    work_keys = [] # Extract only work_key

    for book in data.get("docs", []):

        key = book.get("key")

        if key:
            work_keys.append(key)

    return work_keys
