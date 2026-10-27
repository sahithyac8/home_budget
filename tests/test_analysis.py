"""D4/D6: the Pandas/NumPy calculations, checked against numbers worked out by hand from sample_data.sql."""
import unittest

import analysis
from charts import budget_utilization, category_by_month, expense_distribution, monthly_comparison
from tests.helpers import BUDGETS, TRANSACTIONS, _NAME

PNG = b"\x89PNG"


def budgets_for(year, month):
    from decimal import Decimal
    return [{"category_id": c, "category_name": _NAME[c], "budget_amount": Decimal(a)}
            for c, m, y, a in BUDGETS if (y, m) == (year, month)]


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = analysis.transactions_df(TRANSACTIONS)

    # ---- totals and savings (normal data) ----
    def test_october_totals(self):
        # income 60000 + 1500; expenses 15000 + 7800 + 3200 + 4500 + 3900
        self.assertEqual(analysis.period_totals(self.df, 2026, 10),
                         {"income": 61500.0, "expense": 34400.0, "savings": 27100.0, "savings_rate": 44.1})

    def test_year_total_adds_up_all_months(self):
        t = analysis.period_totals(self.df, 2026, 0)
        self.assertEqual(t["income"], 121500.0)
        self.assertEqual(t["expense"], 22600.0 + 25100.0 + 34400.0)

    def test_monthly_summary_has_twelve_rows_and_correct_savings(self):
        s = analysis.monthly_summary(self.df, 2026)
        self.assertEqual(len(s), 12)
        sep = s[s["month"] == 9].iloc[0]
        self.assertEqual((sep["income"], sep["expense"], sep["savings"]), (60000.0, 25100.0, 34900.0))
        self.assertEqual(float(s[s["month"] == 1].iloc[0]["expense"]), 0.0)  # months without data are zero

    def test_month_without_income_has_negative_savings_and_zero_rate(self):
        aug = analysis.monthly_summary(self.df, 2026).query("month == 8").iloc[0]
        self.assertEqual((aug["income"], aug["expense"], aug["savings"], aug["savings_rate"]),
                         (0.0, 22600.0, -22600.0, 0.0))

    def test_savings_report(self):
        r = analysis.savings_report(analysis.monthly_summary(self.df, 2026))
        self.assertEqual(r["total_savings"], 121500.0 - 82100.0)
        self.assertEqual(r["deficit_months"], 1)
        self.assertEqual(r["active_months"], 3)
        self.assertTrue(r["best_month"].startswith("Sep"))
        self.assertTrue(r["worst_month"].startswith("Aug"))

    # ---- category analysis ----
    def test_category_expense_sorted_with_shares(self):
        c = analysis.category_expense(self.df, 2026, 10)
        self.assertEqual(list(c["category_name"])[:2], ["Rent", "Groceries"])
        self.assertEqual(c.iloc[0]["amount"], 15000.0)
        self.assertEqual(c.iloc[0]["pct"], 43.6)
        self.assertAlmostEqual(c["pct"].sum(), 100.0, delta=0.3)

    def test_category_month_pivot(self):
        p = analysis.category_month_pivot(self.df, 2026)
        self.assertEqual(p.loc["Rent", "Total"], 45000.0)
        self.assertEqual(p.loc["Groceries", 9], 6200.0)
        self.assertEqual(list(p.columns), list(range(1, 13)) + ["Total"])

    # ---- budget violations, including boundaries ----
    def test_october_budget_statuses(self):
        s = analysis.budget_status(self.df, budgets_for(2026, 10), 2026, 10).set_index("category_name")
        self.assertEqual(s.loc["Entertainment", "status"], "Over")
        self.assertEqual(s.loc["Entertainment", "over_by"], 900.0)
        self.assertEqual(s.loc["Entertainment", "utilization"], 130.0)
        self.assertEqual(s.loc["Groceries", "status"], "Over")
        self.assertEqual(s.loc["Healthcare", "status"], "Over")
        self.assertEqual(s.loc["Education", "status"], "Warning")  # 90%
        self.assertEqual(sorted(s[s["status"] == "Over"].index), ["Entertainment", "Groceries", "Healthcare"])

    def test_boundaries_exactly_100_percent_is_not_over_and_80_percent_is_warning(self):
        s = analysis.budget_status(self.df, budgets_for(2026, 8), 2026, 8).set_index("category_name")
        self.assertEqual(s.loc["Groceries", "status"], "Warning")     # 5600 of 5600 = 100%, not above the limit
        self.assertEqual(s.loc["Groceries", "over_by"], 0.0)
        self.assertEqual(s.loc["Utilities", "status"], "Warning")     # 2000 of 2500 = exactly 80%
        self.assertEqual(s.loc["Transportation", "status"], "OK")     # budget but no spending
        self.assertEqual(s.loc["Transportation", "utilization"], 0.0)

    def test_no_budgets_gives_empty_table(self):
        self.assertTrue(analysis.budget_status(self.df, [], 2026, 10).empty)

    # ---- empty dataset ----
    def test_empty_dataset_everywhere(self):
        empty = analysis.transactions_df([])
        self.assertEqual(analysis.period_totals(empty, 2026, 10),
                         {"income": 0.0, "expense": 0.0, "savings": 0.0, "savings_rate": 0.0})
        summary = analysis.monthly_summary(empty, 2026)
        self.assertEqual(len(summary), 12)
        self.assertEqual(summary["expense"].sum(), 0.0)
        self.assertTrue(analysis.category_expense(empty, 2026, 10).empty)
        self.assertTrue(analysis.category_month_pivot(empty, 2026).empty)
        self.assertTrue(analysis.budget_suggestions(empty, 2026, 10).empty)
        self.assertIsNone(analysis.savings_report(summary))
        status = analysis.budget_status(empty, budgets_for(2026, 10), 2026, 10)
        self.assertTrue((status["spent"] == 0).all() and (status["status"] == "OK").all())
        self.assertEqual(analysis.insights(empty, None, 2026, 10)[0]["level"], "info")

    def test_charts_render_png_for_data_and_for_empty_data(self):
        empty = analysis.transactions_df([])
        status = analysis.budget_status(self.df, budgets_for(2026, 10), 2026, 10)
        for png in (expense_distribution(analysis.category_expense(self.df, 2026, 10), "t"),
                    monthly_comparison(analysis.monthly_summary(self.df, 2026), 2026),
                    budget_utilization(status, "t"),
                    category_by_month(analysis.category_month_pivot(self.df, 2026), 2026),
                    expense_distribution(analysis.category_expense(empty, 2026, 10), "t"),
                    monthly_comparison(analysis.monthly_summary(empty, 2026), 2026),
                    budget_utilization(analysis.budget_status(empty, [], 2026, 10), "t"),
                    category_by_month(analysis.category_month_pivot(empty, 2026), 2026)):
            self.assertEqual(png[:4], PNG)


class FeatureTests(unittest.TestCase):
    """Feature 1 (smart insights) and feature 3 (budget suggestions)."""

    @classmethod
    def setUpClass(cls):
        cls.df = analysis.transactions_df(TRANSACTIONS)

    def texts(self, year, month):
        status = analysis.budget_status(self.df, budgets_for(year, month), year, month) if month else None
        return [i["text"] for i in analysis.insights(self.df, status, year, month)]

    def test_insights_for_october(self):
        texts = self.texts(2026, 10)
        self.assertIn("You saved ₹27,100.00 in Oct 2026, which is 44.1% of your income.", texts)
        self.assertIn("Spending is up 37.1% compared with Sep 2026 (₹25,100.00 to ₹34,400.00).", texts)
        self.assertIn("Rent is your largest expense: ₹15,000.00 (43.6% of spending).", texts)
        self.assertIn("Entertainment is 30% over its budget (over by ₹900.00).", texts)
        self.assertIn("Rent has used 100% of its budget; ₹0.00 left.", texts)

    def test_insights_for_month_without_income(self):
        texts = self.texts(2026, 8)
        self.assertIn("No income is recorded for Aug 2026, so the savings rate is shown as 0%.", texts)

    def test_insights_levels(self):
        levels = {i["level"] for i in analysis.insights(
            self.df, analysis.budget_status(self.df, budgets_for(2026, 10), 2026, 10), 2026, 10)}
        self.assertEqual(levels, {"good", "warning", "info"})

    def test_suggestions_use_previous_months_only(self):
        s = analysis.budget_suggestions(self.df, 2026, 10).set_index("category_name")
        self.assertEqual(s.loc["Groceries", "suggested"], 5900.0)       # (5600 + 6200) / 2
        self.assertEqual(s.loc["Transportation", "suggested"], 1100.0)  # 2100 / 2 = 1050, rounded up
        self.assertEqual(int(s["months_used"].iloc[0]), 2)              # only Aug and Sep have expenses
        self.assertNotIn("Healthcare", s.index)                          # October itself is not used

    def test_suggestions_average_three_months(self):
        s = analysis.budget_suggestions(self.df, 2026, 11).set_index("category_name")
        self.assertEqual(s.loc["Groceries", "average_spend"], 6533.33)
        self.assertEqual(s.loc["Groceries", "suggested"], 6600.0)
        self.assertEqual(s.loc["Rent", "suggested"], 15000.0)
        self.assertEqual(s.loc["Healthcare", "suggested"], 1100.0)

    def test_suggestions_across_a_year_boundary(self):
        # January 2027 looks back at Oct, Nov, Dec 2026 -> only October has data.
        s = analysis.budget_suggestions(self.df, 2027, 1).set_index("category_name")
        self.assertEqual(int(s["months_used"].iloc[0]), 1)
        self.assertEqual(s.loc["Rent", "suggested"], 15000.0)

    def test_no_history_means_no_suggestions(self):
        self.assertTrue(analysis.budget_suggestions(self.df, 2026, 8).empty)


if __name__ == "__main__":
    unittest.main()
