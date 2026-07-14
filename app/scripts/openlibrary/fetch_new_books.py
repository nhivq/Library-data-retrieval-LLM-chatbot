from app.scripts.openlibrary.fetch_work import fetch_work, save_work
import requests
import time


OUTPUT_FOLDER = (
    "data/raw/works"
)


def search_books(query):

    url = (
        "https://openlibrary.org/search.json"
        f"?q={query}"
    )


    response = requests.get(url)

    data = response.json()


    keys = []


    for book in data["docs"]:

        if "key" in book:

            keys.append(
                book["key"]
            )


    return keys



def fetch_new_books():

    keys = search_books(
        "fiction"
    )


    for key in keys:

        print(
            "Fetching",
            key
        )


        work = fetch_work(
            key
        )


        if work:

            save_work(
                work,
                OUTPUT_FOLDER
            )


        time.sleep(0.1)



if __name__ == "__main__":

    fetch_new_books()