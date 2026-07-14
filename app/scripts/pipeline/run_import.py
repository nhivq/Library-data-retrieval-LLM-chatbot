from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app.scripts.pipeline.queries import QUERIES
    from app.scripts.pipeline.ingest_books import run_pipeline
    from app.scripts.pipeline.config import PAGE_SIZE
except ModuleNotFoundError:
    from app.scripts.pipeline.queries import QUERIES
    from app.scripts.pipeline.ingest_books import run_pipeline
    from app.scripts.pipeline.config import PAGE_SIZE


def run_import():

    total_saved = 0
    total_skipped = 0
    total_failed = 0

    for query in QUERIES:
        print(f"Starting {query}")

        for page in range(1, 3):
            print(f"Page {page}")

            result = run_pipeline(
                query=query,
                page=page,
                limit=PAGE_SIZE
            )

            total_saved += result["saved"]
            total_skipped += result["skipped"]
            total_failed += result["failed"]

            print(
                "Page summary:",
                f"saved={result['saved']}",
                f"skipped={result['skipped']}",
                f"failed={result['failed']}"
            )

    print(
        "Import summary:",
        f"saved={total_saved}",
        f"skipped={total_skipped}",
        f"failed={total_failed}"
    )


if __name__ == "__main__":
    run_import()
