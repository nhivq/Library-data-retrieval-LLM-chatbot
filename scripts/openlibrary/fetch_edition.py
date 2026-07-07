try:
    from scripts.openlibrary.client import get
except ModuleNotFoundError:
    from client import get
import json
from pathlib import Path


def fetch_editions(work_key):

    data = get(f"{work_key}/editions.json")

    filename = (work_key.split("/")[-1]+ "_editions.json")

    path = Path(__file__).resolve().parents[2]/"data"/"raw"/"editions"/filename

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
