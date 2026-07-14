import json
import os


CLEAN_AUTHOR_FOLDER = ("data/clean/authors")


def validate_author(author):
    errors = []

    if not author.get("author_key"):
        errors.append("missing author_key")

    if not author.get("author_name"):
        errors.append("missing author_name")

    return errors


def validate_authors():

    total = 0
    failed = 0

    for filename in os.listdir(CLEAN_AUTHOR_FOLDER):

        if not filename.endswith(".json"):
            continue

        total += 1

        path = os.path.join(
            CLEAN_AUTHOR_FOLDER,
            filename
        )

        with open(
            path,
            encoding="utf-8"
        ) as f:

            author = json.load(f)

        errors = validate_author(author)

        if errors:

            failed += 1

            print(
                filename,
                errors
            )

    print("Total:", total)

    print("Failed:", failed)


if __name__ == "__main__":
    validate_authors()