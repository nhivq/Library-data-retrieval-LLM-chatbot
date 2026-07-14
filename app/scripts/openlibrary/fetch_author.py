try:
    from app.scripts.openlibrary.client import get
except ModuleNotFoundError:
    from app.scripts.openlibrary.client import get

import json
from pathlib import Path


def fetch_author(author_key):

    data = get(f"{author_key}.json")

    filename = (author_key.split("/")[-1] + ".json")

    path = Path(__file__).resolve().parents[2] / "data" / "raw" / "authors" / filename

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    return data


if __name__ == "__main__":
    fetch_author("/authors/OL26320A")
