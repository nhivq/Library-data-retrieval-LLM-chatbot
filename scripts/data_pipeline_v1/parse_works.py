import gzip
import json
import random

WORK_FILE = "../data/ol_dump_works_2026-04-30.txt.gz"

# Create empty list
books = []

used_author_keys = set() # Collect used author keys while parsing books
counter = 0
MAX_BOOKS = 100000

with gzip.open(WORK_FILE, "rt", encoding="utf-8") as file:

    for line in file:

        try:
            # Split line into columns
            # Fixed: Added max split = 4 to prevent python to split
            #every tab it sees
            parts = line.strip().split("\t", 4)
            # Get JSON part
            json_text = parts[4]
            # Convert JSON text → Python dictionary
            data = json.loads(json_text)

            work_key = data.get("key")
            title = data.get("title")
            if not title:
                continue
            tags = data.get("subjects", [])
            # Đổi format data từ ISO sang ngày tháng only
            publish_date = (
                data.get("created", {})
                .get("value", "")
                .split("T")[0]
            )

            author_entries = data.get("authors", [])
            author_keys = []
            for a in author_entries:
                author_key = (a.get("author", {}).get("key"))
                if author_key:
                    author_keys.append(author_key)
                    used_author_keys.add(author_key)

            # Temporary generated ratings
            # Real OpenLibrary ratings are skipped because
            # project focus is query/API/database flow

            rating = round(random.uniform(3.0, 4.8), 1)

            # Create ONE book object
            book = {
                "work_key" : work_key,
                "title": title,
                "author_keys": author_keys,
                "tags": tags,
                "publish_date": publish_date,
                "rating" : rating
            }

            books.append(book)

            counter += 1
            if counter >= MAX_BOOKS:
                print("Reached Limit")
                break

        except Exception as e:
            print(f"Error: {e}")
            continue

# Save all books
with open("../output/books.json", "w", encoding="utf-8") as out:
    json.dump(books, out, ensure_ascii=False, indent=2)

with open("../output/used_author_keys.json", "w", encoding="utf-8") as f:
    json.dump(list(used_author_keys), f, indent=2)

print(f"Saved {len(books)} books")