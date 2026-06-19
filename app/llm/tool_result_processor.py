import json

def process_tool_result(
        tool_name: str, 
        tool_text: str
):

    tool_data = json.loads(tool_text)

    compact = []

    if tool_data and isinstance(tool_data, list):

        first = tool_data[0]

        # search_books result
        if "title" in first:

            for book in tool_data[:5]:
                compact.append(
                    {
                        "work_key": book.get("work_key"),
                        "title": book.get("title"),
                        "publish_date": book.get("publish_date"),
                        "rating": book.get("rating"),
                        "authors": book.get("authors"),
                        "tags": book.get("tags")[:3] if book.get("tags") else None,
                    }
                )

        # search_authors result
        elif "author_name" in first:

            for author in tool_data[:20]:
                compact.append(
                    {
                        "author_name": author.get("author_name"),
                        "books": (
                            author.get("books", [])[:5]
                        )
                    }
                )

        else:
            compact = tool_data[:10]

    elif isinstance(tool_data, dict):

        compact = tool_data

    else:

        compact = tool_data

    compact_text = json.dumps(
        compact,
        ensure_ascii=False
    )

    return (
        tool_data,
        compact_text
    )
