try:
    from app.scripts.openlibrary.client import get
except ModuleNotFoundError:
    from app.scripts.openlibrary.client import get
import json
from pathlib import Path


def fetch_work(work_key):

    data = get(f"{work_key}.json")

    if data.get("type", {}).get("key") == "/type/redirect":
        data = get(f"{data['location']}.json")

    filename = (work_key.split("/")[-1] + ".json")

    path = Path(__file__).resolve().parents[2] / "data" / "raw" / "works" / filename

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
    fetch_work("/works/OL45883W")
