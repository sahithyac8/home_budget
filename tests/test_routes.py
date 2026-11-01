"""D6: end-to-end checks of the Flask routes with the database replaced by FakeDB."""
import io
import json
import unittest
from pathlib import Path

from tests.helpers import pymysql  # the test helpers provide a stand-in when the driver is not installed

from tests.helpers import AppTestCase

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "sample_import.csv"
GOOD_FORM = {"transaction_date": "2026-10-24", "transaction_type": "expense", "category_id": "5",
             "amount": "250.75", "description": "Vegetables"}


class PageTests(AppTestCase):
    def test_every_page_loads_with_sample_data(self):
        for url in ["/dashboard", "/dashboard?year=2026&month=10", "/transactions", "/transactions?type=expense&month=2026-10",
                    "/transactions/add", "/transactions/15/edit", "/categories", "/budgets?year=2026&month=10",
                    "/budgets?year=2026&month=11", "/reports?year=2026&month=0", "/reports?year=2026&month=10",
                    "/import"]:
            with self.subTest(url=url):
                self.get_text(url)

    def test_charts_return_png(self):
        for name in ["distribution", "monthly", "budget", "category_month"]:
            with self.subTest(chart=name):
                r = self.client.get(f"/chart/{name}.png?year=2026&month=10")
                self.assertEqual((r.status_code, r.mimetype), (200, "image/png"))
                self.assertEqual(r.data[:4], b"\x89PNG")

    def test_unknown_chart_and_whole_year_budget_chart(self):
        self.assertEqual(self.client.get("/chart/nope.png").status_code, 404)
        self.assertEqual(self.client.get("/chart/budget.png?year=2026&month=0").status_code, 400)

    def test_unknown_page_shows_friendly_404(self):
        self.assertIn("Page not found", self.get_text("/no-such-page", 404))

    def test_dashboard_lists_violations_and_insights(self):
        html = self.get_text("/dashboard?year=2026&month=10")
        self.assertIn("Budget limits exceeded", html)
        self.assertIn("Entertainment", html)
        self.assertIn("₹61,500.00", html)
        self.assertIn("Smart insights", html)
        self.assertIn("You saved ₹27,100.00", html)

    def test_out_of_range_period_values_are_clamped(self):
        self.get_text("/dashboard?year=1900&month=99")
        self.get_text("/dashboard?month=0")  # the dashboard always shows a single month
        self.get_text("/reports?year=abc&month=xyz")

    def test_reports_show_deficit_month_and_captions(self):
        html = self.get_text("/reports?year=2026&month=8")
        self.assertIn("How to read this chart", html)
        self.assertIn("No income is recorded for Aug 2026", html)


class TransactionCrudTests(AppTestCase):
    def test_add_valid_transaction(self):
        r = self.client.post("/transactions/add", data=GOOD_FORM)
        self.assertEqual(r.status_code, 302)
        sql, args = self.fake.writes[-1]
        self.assertTrue(sql.startswith("INSERT INTO transactions"))
        self.assertEqual(str(args["amount"]), "250.75")

    def test_add_rejects_invalid_input_and_writes_nothing(self):
        bad_forms = [
            dict(GOOD_FORM, amount="-5"), dict(GOOD_FORM, amount="0"), dict(GOOD_FORM, amount="abc"),
            dict(GOOD_FORM, amount="1.999"), dict(GOOD_FORM, amount="10000000000"),
            dict(GOOD_FORM, transaction_date="2026-02-30"), dict(GOOD_FORM, transaction_date=""),
            dict(GOOD_FORM, transaction_type="gift"), dict(GOOD_FORM, category_id="1"),  # income category
            dict(GOOD_FORM, category_id="999"), dict(GOOD_FORM, category_id=""),
        ]
        for form in bad_forms:
            with self.subTest(form=form):
                r = self.client.post("/transactions/add", data=form)
                self.assertEqual(r.status_code, 400)
        self.assertEqual(self.fake.writes, [])

    def test_form_is_shown_again_with_the_users_input(self):
        html = self.client.post("/transactions/add", data=dict(GOOD_FORM, amount="-5")).get_data(as_text=True)
        self.assertIn('value="-5"', html)
        self.assertIn("greater than 0", html)

    def test_boundary_amounts_are_accepted(self):
        for amount in ["0.01", "9999999999.99"]:
            with self.subTest(amount=amount):
                self.assertEqual(self.client.post("/transactions/add", data=dict(GOOD_FORM, amount=amount)).status_code, 302)

    def test_edit_transaction(self):
        r = self.client.post("/transactions/15/edit", data=dict(GOOD_FORM, amount="4000"))
        self.assertEqual(r.status_code, 302)
        sql, args = self.fake.writes[-1]
        self.assertTrue(sql.startswith("UPDATE transactions"))
        self.assertEqual(args["transaction_id"], 15)

    def test_edit_invalid_does_not_update(self):
        self.assertEqual(self.client.post("/transactions/15/edit", data=dict(GOOD_FORM, amount="x")).status_code, 400)
        self.assertEqual(self.fake.writes, [])

    def test_edit_missing_record_is_404(self):
        self.assertEqual(self.client.get("/transactions/9999/edit").status_code, 404)
        self.assertEqual(self.client.post("/transactions/9999/edit", data=GOOD_FORM).status_code, 404)

    def test_delete_transaction(self):
        self.assertEqual(self.client.post("/transactions/15/delete").status_code, 302)
        self.assertTrue(self.fake.writes[-1][0].startswith("DELETE FROM transactions"))

    def test_delete_needs_post(self):
        self.assertEqual(self.client.get("/transactions/15/delete").status_code, 405)

    def test_invalid_month_filter_is_ignored_with_a_message(self):
        self.assertIn("Ignored invalid month filter", self.get_text("/transactions?month=banana"))


class CategoryAndBudgetTests(AppTestCase):
    def test_add_category(self):
        self.client.post("/categories", data={"category_name": "Pets", "category_type": "expense"})
        self.assertTrue(self.fake.writes[-1][0].startswith("INSERT INTO categories"))

    def test_add_category_validation(self):
        for form in [{"category_name": "", "category_type": "expense"},
                     {"category_name": "x" * 51, "category_type": "expense"},
                     {"category_name": "Pets", "category_type": "other"}]:
            with self.subTest(form=form):
                self.client.post("/categories", data=form)
        self.assertEqual(self.fake.writes, [])

    def test_duplicate_category_shows_message(self):
        self.fake.execute_error = pymysql.err.IntegrityError("duplicate")
        r = self.client.post("/categories", data={"category_name": "Rent", "category_type": "expense"}, follow_redirects=True)
        self.assertIn("That category already exists.", r.get_data(as_text=True))

    def test_cannot_delete_category_with_transactions(self):
        self.fake.execute_error = pymysql.err.IntegrityError("foreign key")
        r = self.client.post("/categories/5/delete", follow_redirects=True)
        self.assertIn("Cannot delete a category that has transactions.", r.get_data(as_text=True))

    def test_save_budgets(self):
        self.client.post("/budgets", data={"year": "2026", "month": "11", "budget_5": "6600", "budget_6": "",
                                           "budget_8": "0", "budget_9": "abc", "budget_10": "-5"})
        statements = [w[0] for w in self.fake.writes]
        self.assertTrue(any(s.startswith("INSERT INTO monthly_budgets") for s in statements))
        inserted = [w for w in self.fake.writes if w[0].startswith("INSERT INTO monthly_budgets")]
        self.assertEqual(len(inserted), 1)  # only Groceries was valid; abc and -5 were skipped
        self.assertTrue(any(s.startswith("DELETE FROM monthly_budgets") for s in statements))

    def test_budget_suggestions_are_listed_and_can_prefill_the_form(self):
        html = self.get_text("/budgets?year=2026&month=11")
        self.assertIn("Suggested limits", html)
        self.assertIn("₹6,600.00", html)
        self.assertNotIn("Nothing is saved until", html)
        pre = self.get_text("/budgets?year=2026&month=11&suggest=1")
        self.assertIn("Nothing is saved until you press Save budgets", pre)
        self.assertIn('value="6600.00"', pre)
        self.assertEqual(self.fake.writes, [])  # pre-filling never writes to the database

    def test_no_suggestions_without_history(self):
        self.assertNotIn("Suggested limits", self.get_text("/budgets?year=2026&month=8"))


class EmptyDatabaseTests(AppTestCase):
    fake_kwargs = {"transactions": [], "budgets": []}

    def test_all_pages_and_charts_work_with_no_data(self):
        for url in ["/dashboard", "/transactions", "/budgets", "/reports", "/reports?month=10", "/categories", "/import",
                    "/api/transactions", "/api/summary", "/api/budget-status", "/api/insights"]:
            with self.subTest(url=url):
                self.get_text(url)
        for name in ["distribution", "monthly", "category_month"]:
            self.assertEqual(self.client.get(f"/chart/{name}.png").data[:4], b"\x89PNG")
        self.assertEqual(self.client.get("/chart/budget.png?month=10").data[:4], b"\x89PNG")

    def test_empty_exports_contain_only_headers(self):
        self.assertEqual(self.get_text("/export/transactions.csv").strip(),
                         "transaction_date,transaction_type,category,amount,description")


class DatabaseErrorTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.fake.down = True

    def test_health_check_reports_database_down(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.get_json(), {"status": "error", "database": "down"})

    def test_pages_show_friendly_503_instead_of_a_stack_trace(self):
        for url in ["/dashboard", "/transactions", "/reports", "/budgets", "/api/summary"]:
            with self.subTest(url=url):
                self.assertIn("Database unavailable", self.get_text(url, 503))

    def test_write_failure_returns_503(self):
        self.assertEqual(self.client.post("/transactions/add", data=GOOD_FORM).status_code, 503)


class HealthAndApiTests(AppTestCase):
    def test_health_ok(self):
        r = self.client.get("/health")
        self.assertEqual((r.status_code, r.get_json()), (200, {"status": "ok", "database": "up"}))

    def test_api_transactions(self):
        rows = self.client.get("/api/transactions").get_json()
        self.assertEqual(len(rows), 15)
        self.assertEqual(rows[0], {"transaction_id": 15, "transaction_date": "2026-10-20",
                                   "transaction_type": "expense", "category": "Entertainment",
                                   "amount": 3900.0, "description": "Weekend trip"})

    def test_api_summary(self):
        body = self.client.get("/api/summary?year=2026&month=10").get_json()
        self.assertEqual(body["totals"]["savings"], 27100.0)
        self.assertEqual(len(body["monthly"]), 12)

    def test_api_budget_status(self):
        body = self.client.get("/api/budget-status?year=2026&month=10").get_json()
        over = [c["category_name"] for c in body["categories"] if c["status"] == "Over"]
        self.assertEqual(sorted(over), ["Entertainment", "Groceries", "Healthcare"])

    def test_api_insights(self):
        body = self.client.get("/api/insights?year=2026&month=10").get_json()
        self.assertTrue(any("27,100.00" in i["text"] for i in body["insights"]))


class ExportImportRouteTests(AppTestCase):
    def test_export_all_transactions(self):
        r = self.client.get("/export/transactions.csv")
        self.assertEqual(r.mimetype, "text/csv")
        self.assertIn("attachment; filename=transactions.csv", r.headers["Content-Disposition"])
        self.assertEqual(len(r.get_data(as_text=True).splitlines()), 16)

    def test_export_filtered_by_month(self):
        lines = self.get_text("/export/transactions.csv?year=2026&month=9").splitlines()
        self.assertEqual(len(lines), 6)  # header + 5 September records

    def test_export_monthly_summary(self):
        body = self.get_text("/export/monthly-summary.csv?year=2026")
        self.assertIn("Oct,61500.00,34400.00,27100.00,44.1", body)

    def upload(self, content, name="data.csv"):
        data = content if isinstance(content, bytes) else content.encode("utf-8")
        return self.client.post("/import", data={"file": (io.BytesIO(data), name)},
                                content_type="multipart/form-data")

    def test_import_sample_file_saves_valid_rows_and_lists_rejected_rows(self):
        r = self.upload(SAMPLE_CSV.read_bytes(), "sample_import.csv")
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        sql, rows = self.fake.writes[-1]
        self.assertTrue(sql.startswith("MANY INSERT INTO transactions"))
        self.assertEqual(len(rows), 6)
        self.assertIn("Rows saved", html)
        self.assertIn("Gym", html)
        self.assertIn("is not an income category", html)
        self.assertIn("at most 2 decimal places", html)

    def test_import_with_only_invalid_rows_writes_nothing(self):
        self.upload("transaction_date,transaction_type,category,amount\nbad,expense,Rent,10\n")
        self.assertEqual(self.fake.writes, [])

    def test_import_without_a_file(self):
        r = self.client.post("/import", data={}, content_type="multipart/form-data")
        self.assertIn("Choose a CSV file first.", r.get_data(as_text=True))

    def test_import_rejects_non_utf8_file(self):
        self.assertIn("UTF-8", self.upload(b"\xff\xfe\x00bad").get_data(as_text=True))
        self.assertEqual(self.fake.writes, [])

    def test_import_rejects_wrong_columns(self):
        self.assertIn("Missing column(s)", self.upload("a,b,c\n1,2,3\n").get_data(as_text=True))

    def test_import_rejects_oversized_file(self):
        self.assertEqual(self.upload(b"x" * 1_100_000).status_code, 413)

    def test_import_database_failure_is_reported(self):
        self.fake.execute_error = pymysql.err.OperationalError("lost connection")
        r = self.upload(SAMPLE_CSV.read_bytes())
        self.assertEqual(r.status_code, 503)


if __name__ == "__main__":
    unittest.main()
