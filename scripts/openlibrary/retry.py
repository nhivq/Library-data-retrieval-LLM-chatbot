import time


def retry(
    func,
    attempts=3
):

    for i in range(attempts):

        try:

            return func()

        except Exception:

            print(f"Retry {i+1}")
            time.sleep(2)

    raise Exception(
        "Failed after retry"
    )