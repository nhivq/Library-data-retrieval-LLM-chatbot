import json

def process_tool_result(
        tool_name: str, 
        tool_text: str
):
    """Parse and compact MCP tool output before giving it back to the LLM.

    Database tools can return large arrays. The model usually needs only the
    most relevant fields, so this function keeps context usage low while
    preserving enough information to answer the user and cite work keys.
    """

    tool_data = json.loads(tool_text)

    compact = []

    if tool_data and isinstance(tool_data, list):

        first = tool_data[0]

        # Book-like results share the "title" field across search, semantic,
        # hybrid, recommendation, and similar-book tools.
        if "title" in first:

            for book in tool_data[:5]:
                compact.append(
                    {
                        "work_key": book.get("work_key"),
                        "title": book.get("title"),
                        "publish_date": book.get("publish_date"),
                        "rating": book.get("rating"),
                        "cover_id": book.get("cover_id"),
                        "recommendation_score": book.get("recommendation_score"),
                        "matched_concept_count": book.get("matched_concept_count"),
                        "concept_count": book.get("concept_count"),
                        "similarity_score": book.get("similarity_score"),
                        "semantic_score": book.get("semantic_score"),
                        "keyword_score": book.get("keyword_score"),
                        "hybrid_score": book.get("hybrid_score"),
                        "authors": book.get("authors"),
                        "tags": book.get("tags")[:3] if book.get("tags") else None,
                    }
                )

        # Author search can return many rows, so keep more authors but limit the
        # nested book title lists.
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
