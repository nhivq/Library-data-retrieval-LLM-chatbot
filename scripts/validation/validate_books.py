import json
import os


CLEAN_BOOK_FOLDER = (
    "data/clean/works"
)


def validate_book(book):

    errors = []

    if not book.get("work_key"):
        errors.append("missing work_key")

    if not book.get("title"):
        errors.append("missing title")

    return errors



def validate_books():

    total = 0
    failed = 0

    for filename in os.listdir(CLEAN_BOOK_FOLDER):

        if not filename.endswith(".json"):
            continue

        total += 1

        path = os.path.join(
            CLEAN_BOOK_FOLDER,
            filename
        )

        with open(
            path,
            encoding="utf-8"
        ) as f:

            book = json.load(f)

        errors = validate_book(book)

        if errors:

            failed += 1

            print(
                filename,
                errors
            )

    print("Total:", total)

    print("Failed:", failed)


if __name__ == "__main__":
    validate_books()