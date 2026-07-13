import pytest


class FakeCursor:
    def __init__(self, fetchone_results=None, fetchall_results=None, rowcount=0, fail_on_execute=False):
        self.fetchone_results = list(fetchone_results or [])
        self.fetchall_results = list(fetchall_results or [])
        self.rowcount = rowcount
        self.fail_on_execute = fail_on_execute
        self.executed = []
        self.closed = False

    def execute(self, query, params=None):
        if self.fail_on_execute:
            raise RuntimeError("database error")

        self.executed.append((query, params))

    def fetchone(self):
        if self.fetchone_results:
            return self.fetchone_results.pop(0)

        return None

    def fetchall(self):
        if self.fetchall_results:
            return self.fetchall_results.pop(0)

        return []

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursors):
        self.cursors = list(cursors)
        self.created_cursors = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, *args, **kwargs):
        cursor = self.cursors.pop(0)
        self.created_cursors.append(cursor)
        return cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def sample_book():
    return {
        "work_key": "/works/OL1W",
        "title": "Dune",
        "tags": ["science fiction"],
        "publish_date": "1965-08-01",
        "rating": 4.8,
        "cover_id": 123,
        "authors": ["Frank Herbert"],
    }
