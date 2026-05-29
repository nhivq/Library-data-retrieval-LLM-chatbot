from routes import bookmarks

books = [
    {
        "title": "World History",
        "rating": 4.5,
        "work_key": "OL123W"
    },

    {
        "title": "Ancient History",
        "rating": 4.2,
        "work_key": "OL456W"
    },

    {
        "title": "Python Basics",
        "rating": 3.9,
        "work_key": "OL789W"
    }
]

def search_books(
    q: str,
    min_rating: float
):

    results = []

    for book in books:

        if (
            q.lower() in book["title"].lower()
            and
            book["rating"] >= min_rating
        ):

            results.append(book)

    return results

def get_book(work_key: str):
    for book in books:
        if book["work_key"] == work_key:
            return book

    return None

bookmarks = []


def save_bookmark(
    user_id: int,
    work_key: str
):

    bookmark = {
        "user_id": user_id,
        "work_key": work_key
    }

    bookmarks.append(bookmark)

    return "Book saved"

def add_numbers(a: int, b: int) -> int:
    return a + b


def subtract_numbers(a: int, b: int) -> int:
    return a - b


def multiply_numbers(a: int, b: int) -> int:
    return a * b

tool_metadata = [
    {
        "name": "add_numbers",
        "description": "Add two numbers together",
        "parameters": {
            "a": "integer",
            "b": "integer"
        }
    },

    {
        "name": "subtract_numbers",
        "description": "subtract two numbers",
        "parameters": {
            "a": "integer",
            "b": "integer"
        }
    },

{
        "name": "multiply_numbers",
        "description": "Multiply two numbers together",
        "parameters": {
            "a": "integer",
            "b": "integer"
        }
    },

{
    "name":"search_books",
    "description":
    "Search books by title and minimum rating",
    "parameters":{
        "q":"string",
        "min_rating":"number"
    }
},

{
    "name":"get_book",
    "description":
    "Get detailed information for a specific book using its work_key",
    "parameters":{
        "work_key":"string"
    }
},

{
    "name":"save_bookmark",
    "description":
    "Save a specific book to a user's bookmarks",
    "parameters":{
        "work_key":"string",
        "user_id":"integer"
    }
}
]

tools = {
    "search_books": search_books,
    "get_book": get_book,
    "save_bookmark": save_bookmark,
    "add_numbers": add_numbers,
    "subtract_numbers": subtract_numbers,
    "multiply_numbers": multiply_numbers
}

tool_call = {
    "tool":"save_bookmark",
    "arguments":{
        "user_id":"1",
        "work_key":"OL123W"
    }
}

def execute(tool_call):
    tool_name = tool_call["tool"]

    arguments = tool_call["arguments"]

    if tool_name in tools:
        try:
            result = tools[tool_name](**arguments)
            response = {
                "success": True,
                "result": result
            }
        except TypeError:
            response = {
                "success": False,
                "error": "Invalid arguments"
            }
    else:
        response = {
            "success": False,
            "error": "Tool not found"
        }

    return response

print(execute(tool_call))

print(bookmarks)