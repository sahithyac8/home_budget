"""Accounts: register, log in, log out, the login gate, and keeping each user's data separate."""
import unittest

from tests.helpers import pymysql  # the test helpers provide a stand-in when the driver is not installed
from werkzeug.security import generate_password_hash

import auth
from tests.helpers import AppTestCase, USER_ID

GOOD_SIGNUP = {"full_name": "Asha Rao", "email": "asha@example.com",
               "password": "Budget2026", "confirm": "Budget2026"}


class LoggedOutTests(AppTestCase):
    logged_in = False

    def test_public_pages_open_without_login(self):
        for url in ["/", "/login", "/register", "/health"]:
            with self.subTest(url=url):
                self.get_text(url)

    def test_landing_page_has_signup_and_login_links(self):
        html = self.get_text("/")
        self.assertIn("Create a free account", html)
        self.assertIn('href="/login"', html)
        self.assertIn('href="/register"', html)

    def test_every_private_page_redirects_to_login(self):
        for url in ["/dashboard", "/transactions", "/transactions/add", "/transactions/15/edit", "/categories",
                    "/budgets", "/reports", "/import", "/export/transactions.csv", "/chart/monthly.png"]:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 302)
                self.assertIn("/login?next=", r.headers["Location"])

    def test_private_actions_are_blocked_and_write_nothing(self):
        for url in ["/transactions/add", "/transactions/15/delete", "/categories", "/budgets", "/import"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, data={}).status_code, 302)
        self.assertEqual(self.fake.writes, [])

    def test_api_answers_401_not_a_redirect(self):
        for url in ["/api/transactions", "/api/summary", "/api/budget-status", "/api/insights"]:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 401)
                self.assertIn("log in", r.get_json()["error"])

    def test_unknown_page_is_still_a_friendly_404(self):
        self.assertIn("Page not found", self.get_text("/no-such-page", 404))


class RegisterTests(AppTestCase):
    logged_in = False

    def test_register_creates_user_hash_and_default_categories(self):
        r = self.client.post("/register", data=GOOD_SIGNUP)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/dashboard"))
        (sql, args), (many_sql, rows) = self.fake.writes
        self.assertTrue(sql.startswith("INSERT INTO users"))
        self.assertEqual(args[:2], ("Asha Rao", "asha@example.com"))
        self.assertNotIn("Budget2026", args[2])               # the password itself is never stored
        self.assertTrue(args[2].startswith("pbkdf2:sha256"))
        self.assertTrue(many_sql.startswith("MANY INSERT INTO categories"))
        self.assertEqual(len(rows), 12)
        self.assertTrue(all(row[0] == 2 for row in rows))      # all belong to the new user

    def test_register_logs_the_user_in(self):
        self.client.post("/register", data=GOOD_SIGNUP)
        with self.client.session_transaction() as session:
            self.assertEqual(session["user_id"], 2)

    def test_invalid_signup_is_rejected_and_writes_nothing(self):
        for form in [dict(GOOD_SIGNUP, full_name=""), dict(GOOD_SIGNUP, email="nope"),
                     dict(GOOD_SIGNUP, password="short1", confirm="short1"),
                     dict(GOOD_SIGNUP, confirm="Different2026")]:
            with self.subTest(form=form):
                self.assertEqual(self.client.post("/register", data=form).status_code, 400)
        self.assertEqual(self.fake.writes, [])

    def test_form_keeps_name_and_email_but_never_the_password(self):
        html = self.client.post("/register", data=dict(GOOD_SIGNUP, confirm="x")).get_data(as_text=True)
        self.assertIn('value="Asha Rao"', html)
        self.assertIn('value="asha@example.com"', html)
        self.assertNotIn("Budget2026", html)

    def test_duplicate_email_is_rejected(self):
        r = self.client.post("/register", data=dict(GOOD_SIGNUP, email="Demo@Example.com"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("already registered", r.get_data(as_text=True))
        self.assertEqual(self.fake.writes, [])

    def test_duplicate_email_race_is_handled(self):
        self.fake.execute_error = pymysql.err.IntegrityError("duplicate email")
        r = self.client.post("/register", data=GOOD_SIGNUP)
        self.assertEqual(r.status_code, 400)
        self.assertIn("already registered", r.get_data(as_text=True))

    def test_html_in_name_is_escaped(self):
        html = self.client.post("/register", data=dict(GOOD_SIGNUP, full_name="<script>x</script>", confirm="no")
                                ).get_data(as_text=True)
        self.assertNotIn("<script>x</script>", html)


class LoginTests(AppTestCase):
    logged_in = False

    def setUp(self):
        super().setUp()
        auth._failures.clear()
        # a fast hash keeps the tests quick; the app itself uses 600000 rounds
        self.fake.users[0]["password_hash"] = generate_password_hash("Demo@1234", method="pbkdf2:sha256:1000")

    def login(self, email="demo@example.com", password="Demo@1234", **extra):
        return self.client.post("/login", data=dict(email=email, password=password, **extra))

    def test_correct_login_opens_the_dashboard(self):
        r = self.login()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/dashboard"))
        self.assertIn("Dashboard", self.get_text("/dashboard"))

    def test_email_is_case_insensitive(self):
        self.assertEqual(self.login(email="  DEMO@Example.com ").status_code, 302)

    def test_wrong_password_and_unknown_email_give_the_same_message(self):
        for email, password in [("demo@example.com", "wrong-password1"), ("nobody@example.com", "Demo@1234")]:
            with self.subTest(email=email):
                r = self.login(email, password)
                self.assertEqual(r.status_code, 401)
                self.assertIn("Invalid email or password.", r.get_data(as_text=True))
        self.assertEqual(self.client.get("/dashboard").status_code, 302)  # still logged out

    def test_five_wrong_passwords_lock_the_account_for_a_while(self):
        for _ in range(auth.MAX_FAILURES):
            self.login(password="wrong-password1")
        r = self.login()  # even the right password is refused during the lock
        self.assertEqual(r.status_code, 401)
        self.assertIn("Too many wrong attempts", r.get_data(as_text=True))

    def test_successful_login_resets_the_failure_count(self):
        for _ in range(auth.MAX_FAILURES - 1):
            self.login(password="wrong-password1")
        self.assertEqual(self.login().status_code, 302)
        self.assertNotIn("demo@example.com", auth._failures)

    def test_login_returns_to_the_page_the_user_asked_for(self):
        r = self.client.get("/budgets?month=9")
        self.assertIn("/login?next=/budgets", r.headers["Location"])
        r = self.login(next="/budgets?month=9")
        self.assertTrue(r.headers["Location"].endswith("/budgets?month=9"))

    def test_unsafe_next_urls_are_ignored(self):
        for target in ["//evil.example", "https://evil.example", "/\\evil.example", "javascript:alert(1)"]:
            with self.subTest(target=target):
                self.client.get("/logout")
                r = self.login(next=target)
                self.assertTrue(r.headers["Location"].endswith("/dashboard"))
                with self.client.session_transaction() as s:
                    s.clear()

    def test_logged_in_user_is_sent_away_from_login_and_landing(self):
        self.login()
        for url in ["/", "/login", "/register"]:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 302)
                self.assertTrue(r.headers["Location"].endswith("/dashboard"))

    def test_logout_needs_post_and_ends_the_session(self):
        self.login()
        self.assertEqual(self.client.get("/logout").status_code, 405)
        self.assertEqual(self.client.post("/logout").status_code, 302)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_session_of_a_deleted_user_is_rejected(self):
        self.log_in(user_id=99)  # no such user
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])


class DataSeparationTests(AppTestCase):
    """Each person sees and changes only their own records."""

    def test_every_query_on_money_tables_is_limited_to_the_logged_in_user(self):
        for url in ["/dashboard", "/transactions?type=expense&month=2026-10", "/transactions/add",
                    "/transactions/15/edit", "/categories", "/budgets?suggest=1", "/reports",
                    "/export/transactions.csv", "/export/monthly-summary.csv", "/import", "/api/summary"]:
            self.get_text(url)
        self.client.post("/budgets", data={"year": "2026", "month": "11", "budget_5": "100", "budget_6": ""})
        self.client.post("/categories", data={"category_name": "Pets", "category_type": "expense"})
        self.client.post("/transactions/add", data={"transaction_date": "2026-10-24", "transaction_type": "expense",
                                                    "category_id": "5", "amount": "10", "description": ""})
        self.client.post("/transactions/15/edit", data={"transaction_date": "2026-10-24", "transaction_type": "expense",
                                                        "category_id": "5", "amount": "10", "description": ""})
        self.client.post("/transactions/15/delete")
        self.client.post("/categories/5/delete")
        checked = 0
        for sql, args in self.fake.queries + self.fake.writes:
            if any(t in sql for t in ("transactions", "categories", "monthly_budgets")) and "users" not in sql:
                values = list(args.values()) if isinstance(args, dict) else list(args or [])
                with self.subTest(sql=sql[:70]):
                    self.assertIn("user_id", sql)
                    self.assertIn(USER_ID, values)
                checked += 1
        self.assertGreater(checked, 20)

    def test_imported_rows_belong_to_the_logged_in_user(self):
        import io
        csv_text = "transaction_date,transaction_type,category,amount\n2026-11-01,expense,Rent,100\n"
        self.client.post("/import", data={"file": (io.BytesIO(csv_text.encode()), "a.csv")},
                         content_type="multipart/form-data")
        _, rows = self.fake.writes[-1]
        self.assertEqual([r["user_id"] for r in rows], [USER_ID])

    def test_another_user_sees_nothing_and_cannot_touch_the_records(self):
        self.fake.users.append({"user_id": 2, "full_name": "Other Person", "email": "o@example.com",
                                "password_hash": None})
        self.log_in(user_id=2)
        self.assertIn("No transactions found", self.get_text("/transactions"))
        self.assertEqual(self.client.get("/transactions/15/edit").status_code, 404)
        self.assertEqual(self.client.post("/transactions/15/edit", data={
            "transaction_date": "2026-10-24", "transaction_type": "expense", "category_id": "5",
            "amount": "1", "description": ""}).status_code, 404)
        self.assertEqual(self.client.get("/api/transactions").get_json(), [])
        # someone else's category id is treated as "not a valid category"
        r = self.client.post("/transactions/add", data={"transaction_date": "2026-10-24", "transaction_type": "expense",
                                                        "category_id": "5", "amount": "1", "description": ""})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.fake.writes, [])
        # a delete is always limited to the caller's own id, so it cannot remove user 1's record
        self.client.post("/transactions/15/delete")
        sql, args = self.fake.writes[-1]
        self.assertIn("AND user_id = %s", sql)
        self.assertEqual(args, (15, 2))


class SafetyHeaderTests(AppTestCase):
    def test_pages_carry_safety_headers_and_are_not_cached(self):
        h = self.client.get("/dashboard").headers
        self.assertEqual(h["X-Frame-Options"], "DENY")
        self.assertEqual(h["X-Content-Type-Options"], "nosniff")
        self.assertEqual(h["Cache-Control"], "no-store")

    def test_login_cookie_is_httponly_and_samesite(self):
        self.assertTrue(auth.safe_next_url("/ok") == "/ok" and auth.safe_next_url("//x") is None)
        from app import app
        self.assertTrue(app.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(app.config["SESSION_COOKIE_SAMESITE"], "Lax")


if __name__ == "__main__":
    unittest.main()
