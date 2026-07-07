def merge_book(
    work,
    edition=None
):

    book = work.copy()

    if edition:

        # Edition data fills gaps in the work record; it should not replace
        # first-published work metadata when OpenLibrary already provides it.
        if edition.get("cover_id"):

            book["cover_id"] = (edition["cover_id"])

        if edition.get("publish_date") and not book.get("publish_date"):

            book["publish_date"] = (edition["publish_date"])

        if edition.get("languages"):

            book["languages"] = (edition["languages"])

        if edition.get("publishers"):

            book["publishers"] = (edition["publishers"])

    return book
