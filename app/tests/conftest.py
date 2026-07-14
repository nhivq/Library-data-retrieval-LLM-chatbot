import pytest


class FakeCursor:
    """Small test double for database cursors used by service tests.

    It records SQL and parameters instead of talking to Postgres. That lets the
    tests prove "the service asked the database the right thing" without needing
    a real database server.
    """

    def __init__(self, fetchone_results=None, fetchall_results=None, rowcount=0, fail_on_execute=False):
        # Results are queued in the same order the service will call fetchone()
        # or fetchall(). This keeps tests readable when a function performs
        # several database reads.
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
    """Small test double for database connections.

    The counters make transaction behavior visible. A future maintainer can see
    whether a service commits successful writes or rolls back failed ones.
    """

    def __init__(self, cursors):
        self.cursors = list(cursors)
        self.created_cursors = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, *args, **kwargs):
        # Services may request RealDictCursor or a plain cursor. The fake does
        # not need those options, but accepting them keeps the same call shape.
        cursor = self.cursors.pop(0)
        self.created_cursors.append(cursor)
        return cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def sample_book():
    """Shared realistic book row used across service and route tests."""

    return {
        "work_key": "/works/OL1W",
        "title": "Dune",
        "tags": ["science fiction"],
        "publish_date": "1965-08-01",
        "rating": 4.8,
        "cover_id": 123,
        "authors": ["Frank Herbert"],
    }
