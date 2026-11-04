"""Shared test helpers: an in-memory stand-in for MySQL, loaded with the same data as sample_data.sql.

The tests therefore run on any machine (no MySQL server needed). The real database is checked
separately with the manual steps in docs/TEST_REPORT.md.
"""
import datetime as dt
import sys
import types
import unittest
from decimal import Decimal
from unittest import mock

try:
    import pymysql  # noqa: F401
except ImportError:  # lets the tests run where the MySQL driver is not installed
    class MySQLError(Exception):
        pass

    class OperationalError(MySQLError):
        pass

    class IntegrityError(MySQLError):
        pass

    _stub = types.ModuleType("pymysql")
    _stub.err = types.SimpleNamespace(MySQLError=MySQLError, OperationalError=OperationalError,
                                      IntegrityError=IntegrityError)
    _cursors = types.ModuleType("pymysql.cursors")
    _cursors.DictCursor = object
    _stub.cursors = _cursors
    sys.modules["pymysql"] = _stub
    sys.modules["pymysql.cursors"] = _cursors
    import pymysql  # noqa: F401,E402

import db  # noqa: E402
from app import app  # noqa: E402

D = dt.date
CATEGORIES = [
    {"category_id": 1, "category_name": "Salary", "category_type": "income"},
    {"category_id": 2, "category_name": "Business", "category_type": "income"},
    {"category_id": 3, "category_name": "Interest", "category_type": "income"},
    {"category_id": 4, "category_name": "Other Income", "category_type": "income"},
    {"category_id": 5, "category_name": "Groceries", "category_type": "expense"},
    {"category_id": 6, "category_name": "Rent", "category_type": "expense"},
    {"category_id": 7, "category_name": "Transportation", "category_type": "expense"},
    {"category_id": 8, "category_name": "Healthcare", "category_type": "expense"},
    {"category_id": 9, "category_name": "Education", "category_type": "expense"},
    {"category_id": 10, "category_name": "Entertainment", "category_type": "expense"},
    {"category_id": 11, "category_name": "Utilities", "category_type": "expense"},
    {"category_id": 12, "category_name": "Other Expense", "category_type": "expense"},
]
_NAME = {c["category_id"]: c["category_name"] for c in CATEGORIES}


def txn(i, d, ttype, cat_id, amount, desc):
    return {"transaction_id": i, "transaction_date": d, "transaction_type": ttype,
            "category_id": cat_id, "category_name": _NAME[cat_id],
            "amount": Decimal(amount), "description": desc}


# Same records as sample_data.sql (newest first, like the real query returns them).
TRANSACTIONS = [
    txn(15, D(2026, 10, 20), "expense", 10, "3900.00", "Weekend trip"),
    txn(14, D(2026, 10, 15), "expense", 9, "4500.00", "Course fees"),
    txn(13, D(2026, 10, 10), "expense", 8, "3200.00", "Doctor visit and medicines"),
    txn(12, D(2026, 10, 6), "expense", 5, "7800.00", "Groceries and festival shopping"),
    txn(11, D(2026, 10, 3), "expense", 6, "15000.00", "October rent"),
    txn(10, D(2026, 10, 2), "income", 3, "1500.00", "Savings interest"),
    txn(9, D(2026, 10, 1), "income", 1, "60000.00", "October salary"),
    txn(8, D(2026, 9, 18), "expense", 10, "1800.00", "Movies and dining"),
    txn(7, D(2026, 9, 12), "expense", 7, "2100.00", "Fuel and bus pass"),
    txn(6, D(2026, 9, 7), "expense", 5, "6200.00", "Monthly groceries"),
    txn(5, D(2026, 9, 3), "expense", 6, "15000.00", "September rent"),
    txn(4, D(2026, 9, 1), "income", 1, "60000.00", "September salary"),
    txn(3, D(2026, 8, 14), "expense", 11, "2000.00", None),
    txn(2, D(2026, 8, 9), "expense", 5, "5600.00", "Monthly groceries"),
    txn(1, D(2026, 8, 3), "expense", 6, "15000.00", "August rent"),
]
BUDGETS = [  # (category_id, month, year, amount)
    (5, 10, 2026, "7000.00"), (6, 10, 2026, "15000.00"), (8, 10, 2026, "3000.00"),
    (10, 10, 2026, "3000.00"), (9, 10, 2026, "5000.00"),
    (5, 8, 2026, "5600.00"), (11, 8, 2026, "2500.00"), (7, 8, 2026, "2000.00"), (6, 8, 2026, "15000.00"),
]


USER_ID = 1
USERS = [{"user_id": USER_ID, "full_name": "Demo User", "email": "demo@example.com",
          "password_hash": None}]  # the hash is filled in by the login tests


class FakeCursor:
    """Just enough of a database cursor for db.run_in_transaction()."""

    def __init__(self, fake):
        self.fake, self.lastrowid = fake, 0

    def execute(self, sql, args=None):
        self.fake._check()
        if self.fake.execute_error:
            raise self.fake.execute_error
        self.fake.writes.append((" ".join(sql.split()), args))
        self.lastrowid = len(self.fake.users) + 1

    def executemany(self, sql, rows):
        self.fake._check()
        self.fake.writes.append(("MANY " + " ".join(sql.split()), list(rows)))


class FakeDB:
    """Answers the SQL the app sends, from lists in memory. Records every query and write."""

    def __init__(self, transactions=None, budgets=None):
        self.users = [dict(u) for u in USERS]
        self.queries = []          # every (sql, args) sent to query_all / query_one
        self.categories = [dict(c) for c in CATEGORIES]
        self.transactions = [dict(t) for t in (TRANSACTIONS if transactions is None else transactions)]
        self.budgets = list(BUDGETS if budgets is None else budgets)
        self.month_categories = []  # [{"category_id": .., "status": "added" | "dismissed"}]
        self.writes = []
        self.down = False          # True = behave like MySQL is not reachable
        self.execute_error = None  # an exception to raise on the next write

    def _check(self):
        if self.down:
            raise pymysql.err.OperationalError("MySQL server is not reachable")

    def query_all(self, sql, args=None):
        self._check()
        s = " ".join(sql.split())
        self.queries.append((s, args))
        if args and args[0] != USER_ID:
            return []  # every record in this fake belongs to the demo user, so anyone else sees nothing
        if "FROM month_categories" in s:
            return list(self.month_categories)
        if "FROM monthly_budgets b" in s:
            _, year, month = args
            return [{"category_id": cid, "category_name": _NAME[cid], "budget_amount": Decimal(a)}
                    for cid, m, y, a in self.budgets if (y, m) == (year, month)]
        if "COUNT(t.transaction_id)" in s:
            return [dict(c, txn_count=sum(1 for t in self.transactions if t["category_id"] == c["category_id"]))
                    for c in self.categories]
        if "FROM transactions t" in s:
            return [dict(t) for t in self.transactions]
        if "FROM categories" in s:
            if "category_type='expense'" in s:
                return [c for c in self.categories if c["category_type"] == "expense"]
            return list(self.categories)
        raise AssertionError("FakeDB does not know this SQL: " + s)

    def query_one(self, sql, args=None):
        self._check()
        s = " ".join(sql.split())
        self.queries.append((s, args))
        if s.startswith("SELECT 1"):
            return {"ok": 1}
        if "FROM users WHERE user_id" in s:
            return next((u for u in self.users if u["user_id"] == args[0]), None)
        if "FROM users WHERE email" in s:
            return next((u for u in self.users if u["email"] == args[0]), None)
        if args and len(args) > 1 and args[1] != USER_ID:
            return None  # (id, user_id): the record belongs to the demo user only
        if "FROM categories WHERE category_id" in s:
            return next((c for c in self.categories if c["category_id"] == args[0]), None)
        if "FROM transactions WHERE transaction_id" in s:
            return next((t for t in self.transactions if t["transaction_id"] == args[0]), None)
        raise AssertionError("FakeDB does not know this SQL: " + s)

    def execute(self, sql, args=None):
        self._check()
        if self.execute_error:
            raise self.execute_error
        self.writes.append((" ".join(sql.split()), args))
        return 1

    def execute_many(self, sql, rows):
        self._check()
        if self.execute_error:
            raise self.execute_error
        self.writes.append(("MANY " + " ".join(sql.split()), list(rows)))
        return len(rows)

    def run_in_transaction(self, work):
        self._check()
        return work(FakeCursor(self))


class AppTestCase(unittest.TestCase):
    """Starts the Flask test client with the database replaced by FakeDB."""
    fake_kwargs = {}
    logged_in = True

    def setUp(self):
        self.fake = FakeDB(**self.fake_kwargs)
        for name in ("query_all", "query_one", "execute", "execute_many", "run_in_transaction"):
            patcher = mock.patch.object(db, name, getattr(self.fake, name))
            patcher.start()
            self.addCleanup(patcher.stop)
        app.config["TESTING"] = True
        self.client = app.test_client()
        if self.logged_in:
            self.log_in()

    def log_in(self, user_id=USER_ID):
        """Pretend the person has already logged in (the login form itself is tested in test_auth.py)."""
        with self.client.session_transaction() as session:
            session["user_id"] = user_id

    def get_text(self, url, status=200):
        response = self.client.get(url)
        self.assertEqual(response.status_code, status, f"{url} -> {response.status_code}")
        return response.get_data(as_text=True)
