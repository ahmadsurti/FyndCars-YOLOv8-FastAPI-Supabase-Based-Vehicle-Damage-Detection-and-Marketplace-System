"""
Shared fixtures: an in-memory fake of the supabase-py fluent client.

Supports exactly the builder surface used by the route modules:
  table(name).select(cols, count=) / .insert(row) / .update(row) / .delete()
  chained with .eq/.neq/.gt/.gte/.lt/.lte/.ilike/.contains/.in_
  then .order/.range/.limit/.single, terminated by .execute() → FakeResult(.data, .count)

Inserted rows get id / created_at / viewed_at defaults when absent.
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FakeResult:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class FakeQuery:
    def __init__(self, table, mode, count=None, payload=None):
        self._table = table
        self._mode = mode
        self._count_flag = count
        self._payload = payload
        self._filters = []
        self._order = ("created_at", False)
        self._window = None
        self._single = False

    # -- filters (chainable) --
    def _where(self, fn):
        self._filters.append(fn)
        return self

    def eq(self, col, val):  return self._where(lambda r: r.get(col) == val)
    def neq(self, col, val): return self._where(lambda r: r.get(col) != val)
    def gt(self, col, val):  return self._where(lambda r: r.get(col) is not None and r.get(col) > val)
    def gte(self, col, val): return self._where(lambda r: r.get(col) is not None and r.get(col) >= val)
    def lt(self, col, val):  return self._where(lambda r: r.get(col) is not None and r.get(col) < val)
    def lte(self, col, val): return self._where(lambda r: r.get(col) is not None and r.get(col) <= val)

    def ilike(self, col, pattern):
        needle = str(pattern).replace("%", "").lower()
        return self._where(lambda r: needle in str(r.get(col) or "").lower())

    def contains(self, col, items):
        return self._where(lambda r: all(i in (r.get(col) or []) for i in items))

    def in_(self, col, values):
        return self._where(lambda r: r.get(col) in values)

    # -- shaping --
    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def range(self, start, end):  # PostgREST range is end-inclusive
        self._window = (start, end)
        return self

    def limit(self, n):
        self._window = (0, n - 1)
        return self

    def single(self):
        self._single = True
        return self

    # -- execution --
    def _matching(self):
        return [r for r in self._table.rows if all(f(r) for f in self._filters)]

    def execute(self):
        if self._mode == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            created = []
            for p in payloads:
                row = {"id": str(uuid.uuid4()), "created_at": _now(), "viewed_at": _now(), **p}
                self._table.rows.append(row)
                created.append(row)
            return FakeResult(created)

        if self._mode == "update":
            matches = self._matching()
            for r in matches:
                r.update(self._payload)
            return FakeResult(matches)

        if self._mode == "delete":
            matches = self._matching()
            self._table.rows[:] = [r for r in self._table.rows if r not in matches]
            return FakeResult(matches)

        # select
        col, desc = self._order
        rows = sorted(self._matching(), key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        if self._window:
            start, end = self._window
            rows = rows[start:end + 1]
        if self._single:
            return FakeResult(rows[:1] or None)
        return FakeResult(rows, count=len(rows) if self._count_flag == "exact" else None)


class FakeTable:
    def __init__(self, rows):
        self.rows = rows

    def select(self, _cols="*", count=None):
        return FakeQuery(self, "select", count=count)

    def insert(self, payload):
        return FakeQuery(self, "insert", payload=payload)

    def update(self, payload):
        return FakeQuery(self, "update", payload=payload)

    def delete(self):
        return FakeQuery(self, "delete")


class FakeSupabase:
    def __init__(self, data=None):
        self.tables = {}
        for name, rows in (data or {}).items():
            self.tables[name] = [dict(r) for r in rows]

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = []
        return FakeTable(self.tables[name])


@pytest.fixture
def install_db(monkeypatch):
    """install_db({...}) swaps the route modules' `supabase` for a fake primed with seed data."""
    def _install(data=None):
        fake = FakeSupabase(data)
        import routes.admin
        import routes.listings
        import routes.marketplace
        for module in (routes.listings, routes.admin, routes.marketplace):
            monkeypatch.setattr(module, "supabase", fake)
        return fake
    return _install
