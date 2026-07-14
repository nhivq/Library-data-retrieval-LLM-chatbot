import time
import requests


BASE_URL = "https://openlibrary.org"
HEADERS = {
    "User-Agent": "Library-data-retrieval-LLM-chatbot/0.1"
}
MAX_RETRIES = 3
RETRY_SLEEP = 2


def get(path, params=None):

    if not path.startswith("/"):
        path = "/" + path

    url = BASE_URL + path

    # OpenLibrary can reset or timeout during long runs; retry only transient failures.
    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=30
            )

            if response.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(
                    f"Retryable status code: {response.status_code}",
                    response=response
                )

            response.raise_for_status()

            return response.json()

        except (
            requests.ConnectionError,
            requests.Timeout,
            requests.HTTPError
        ) as e:
            if isinstance(e, requests.HTTPError):
                status_code = None

                if e.response is not None:
                    status_code = e.response.status_code

                if status_code not in (429, 500, 502, 503, 504):
                    raise

            if attempt == MAX_RETRIES:
                raise

            time.sleep(RETRY_SLEEP * attempt)
