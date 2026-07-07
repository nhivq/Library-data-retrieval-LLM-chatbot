import gzip
import json

with open("../output/used_author_keys.json", "r", encoding="utf-8") as f:
    used_author_keys = set(json.load(f))

AUTHOR_FILE = "../data/ol_dump_authors_2026-04-30.txt.gz"
authors = {}
with gzip.open(AUTHOR_FILE, "rt", encoding="utf-8") as file:
    for line in file:
        try:
            parts = line.strip().split("\t")
            json_text = parts[4]
            data = json.loads(json_text)

            author_key = data.get("key")
            author_name = data.get("name")

            if (
                author_key
                and author_name
                and author_key in used_author_keys
            ):
                authors[author_key] = author_name


        except Exception as e:
            print(f"Error: {e}")
            continue

with open("../output/authors.json", "w", encoding="utf-8") as out:
    json.dump(authors, out, ensure_ascii=False, indent=2)