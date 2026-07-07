import json
from collections import Counter
import re

BOOK_FILE="../output/books.json"

with open(BOOK_FILE, "r", encoding="utf-8") as f:
    books=json.load(f)

missing_title=0
missing_author=0
invalid_date=0
null_values=0
long_fields=0
special_characters=0

total_errors=0

# Duplicate Counters
title_counter=Counter()

for book in books:
    # Missing title
    if not book.get("title"):
        missing_title+=1
        total_errors+=1

    # Missing author
    if not book.get("author_keys"):
        missing_author+=1
        total_errors+=1

    # Publish date check
    publish_date=book.get("publish_date", "")
    if publish_date:
        try:
            year=int(publish_date[:4])
            if year<1500 or year>2026:
                invalid_date+=1
                total_errors+=1
        except:
            invalid_date+=1
            total_errors+=1

    # Null check
    for value in book.values():
        if value is None:
            null_values+=1
            total_errors+=1

    # Duplicate title
    title=book.get("title", "")
    if title:
        title_counter[title.lower()]+=1

    # Long fields
    if title and len(title)>300:
        long_fields+=1
        total_errors+=1

    # Special character check
    if title:
        if re.search(r'[<>{}[\]\\|]', title):
            special_characters+=1
    duplicate_titles = 0
    for title, count in title_counter.items():
        if count > 1:
            duplicate_titles += 1

print("="*50)
print(f"Total books: {len(books)}")
print(f"Missing title: {missing_title}")
print(f"Missing author: {missing_author}")
print(f"Invalid publish date: {invalid_date}")
print(f"Null values: {null_values}")
print(f"Duplicate titles: {duplicate_titles}")
print(f"Long fields: {long_fields}")
print(f"Special characters: {special_characters}")
print(f"Total errors: {total_errors}")
print("="*50)