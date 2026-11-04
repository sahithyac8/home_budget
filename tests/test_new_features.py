"""Tests for the month-wise categories, the filtered downloads and the salary budget advice."""
import datetime as dt
import unittest

import analysis
import month_categories
from tests.helpers import AppTestCase, CATEGORIES, TRANSACTIONS


def df_all():
    from app import fetch_transactions  # noqa: F401  (imported only to be sure the app loads)
    return analysis.transactions_df(TRANSACTIONS)


EXPENSE = [c for c in CATEGORIES if c["category_type"] == "expense"]


class MonthCategoryLogic(unittest.TestCase):
    def test_priority_comes_from_earlier_months(self):
        plan = month_categories.category_plan(df_all(), EXPENSE, {}, 2026, 11)
        by = {i["category_name"]: i for i in plan["active"]}
        self.assertEqual(by["Rent"]["priority"], "Core")
        self.assertEqual(by["Groceries"]["priority"], "Core")
        self.assertEqual(by["Education"]["priority"], "Occasional")   # used in 1 of 3 months
        self.assertEqual(plan["active"][0]["priority"], "Core")       # core categories are listed first

    def test_dismissed_suggestion_moves_out_of_the_month(self):
        plan = month_categories.category_plan(df_all(), EXPENSE, {9: "dismissed"}, 2026, 11)
        self.assertNotIn("Education", [i["category_name"] for i in plan["active"]])
        self.assertIn("Education", [i["category_name"] for i in plan["removed"]])

    def test_category_with_transactions_stays(self):
        plan = month_categories.category_plan(df_all(), EXPENSE, {9: "dismissed"}, 2026, 10)
        self.assertIn("Education", [i["category_name"] for i in plan["active"]])

    def test_new_account_gets_starter_suggestions(self):
        plan = month_categories.category_plan(analysis.transactions_df([]), EXPENSE, {}, 2026, 11)
        names = [i["category_name"] for i in plan["active"]]
        self.assertIn("Rent", names)
        self.assertEqual(plan["observed"], 0)


class SalaryAdvice(unittest.TestCase):
    def test_advice_uses_frequent_categories_and_keeps_savings(self):
        plan = analysis.salary_budget_plan(df_all(), 60000, EXPENSE, 2026, 11)
        names = [r["category_name"] for r in plan["rows"]]
        self.assertIn("Rent", names)
        self.assertIn("Groceries", names)
        self.assertEqual(plan["savings"], 12000.0)
        self.assertLessEqual(sum(r["advised"] for r in plan["rows"]), 48000 + 50 * len(names))

    def test_no_history_uses_typical_split(self):
        plan = analysis.salary_budget_plan(analysis.transactions_df([]), 40000, EXPENSE, 2026, 11)
        self.assertTrue(plan["rows"])
        self.assertIn("typical", plan["based_on"])

    def test_zero_salary_gives_nothing(self):
        self.assertEqual(analysis.salary_budget_plan(df_all(), 0, EXPENSE, 2026, 11)["rows"], [])


class Routes(AppTestCase):
    def test_categories_page_is_month_wise(self):
        html = self.get_text("/categories?year=2026&month=11")
        self.assertIn("Nov 2026", html)
        self.assertIn("Core", html)
        self.assertIn("Occasional", html)

    def test_delete_suggestion_for_a_month(self):
        self.client.post("/categories/9/month", data={"year": "2026", "month": "11", "action": "remove"})
        sql, args = self.fake.writes[-1]
        self.assertTrue(sql.startswith("INSERT INTO month_categories"))
        self.assertEqual(args[1:], (9, 2026, 11, "dismissed"))

    def test_cannot_delete_category_used_that_month(self):
        r = self.client.post("/categories/9/month", data={"year": "2026", "month": "10", "action": "remove"},
                             follow_redirects=True)
        self.assertIn("stays in that month", r.get_data(as_text=True))
        self.assertEqual(self.fake.writes, [])

    def test_side_panel_on_every_page(self):
        for url in ["/dashboard", "/transactions", "/categories", "/budgets", "/reports", "/import"]:
            with self.subTest(url=url):
                self.assertIn('class="sidebar"', self.get_text(url))

    def test_export_last_months(self):
        body = self.get_text("/export/transactions.csv?range=custom&months=2")  # relative to today
        self.assertTrue(body.startswith("transaction_date"))
        r = self.client.get("/export/transactions.csv?range=3")
        self.assertIn("last-3-months", r.headers["Content-Disposition"])
        self.assertEqual(self.client.get("/export/transactions.csv?range=custom&months=0").status_code, 302)

    def test_months_start(self):
        from app import months_start
        self.assertEqual(months_start(1, dt.date(2026, 11, 4)), dt.date(2026, 11, 1))
        self.assertEqual(months_start(3, dt.date(2026, 11, 4)), dt.date(2026, 9, 1))
        self.assertEqual(months_start(6, dt.date(2026, 2, 10)), dt.date(2025, 9, 1))

    def test_salary_leads_to_advised_budget(self):
        r = self.client.post("/transactions/add", data={"transaction_date": "2026-11-01", "transaction_type": "income",
                                                        "category_id": "1", "amount": "60000", "description": "Nov"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/budgets?year=2026&month=11&salary=60000.00", r.headers["Location"])
        html = self.get_text("/budgets?year=2026&month=11&salary=60000.00")
        self.assertIn("Advised budget for a salary of", html)
        self.assertIn("Savings", html)


if __name__ == "__main__":
    unittest.main()
