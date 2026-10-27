"""D6: normal, invalid and boundary input for the validation rules (validation.py)."""
import unittest
from decimal import Decimal

from validation import parse_amount, parse_date, validate_transaction

EXPENSE_CAT = {"category_id": 5, "category_name": "Groceries", "category_type": "expense"}
INCOME_CAT = {"category_id": 1, "category_name": "Salary", "category_type": "income"}


class AmountTests(unittest.TestCase):
    def test_valid_amounts_including_boundaries(self):
        for text, expected in [("100", "100"), ("0.01", "0.01"), ("250.75", "250.75"),
                               (" 42.5 ", "42.5"), ("9999999999.99", "9999999999.99")]:
            with self.subTest(text=text):
                amount, error = parse_amount(text)
                self.assertIsNone(error)
                self.assertEqual(amount, Decimal(expected))

    def test_invalid_amounts_are_rejected(self):
        for text in ["0", "-5", "-0.01", "0.001", "100.123", "abc", "", None, "NaN", "Infinity",
                     "10000000000", "10000000000.00", "1,000"]:
            with self.subTest(text=text):
                amount, error = parse_amount(text)
                self.assertIsNone(amount)
                self.assertTrue(error)


class DateTests(unittest.TestCase):
    def test_valid_date(self):
        self.assertEqual(str(parse_date("2026-10-24")), "2026-10-24")
        self.assertEqual(str(parse_date("2024-02-29")), "2024-02-29")  # leap day

    def test_invalid_dates(self):
        for text in ["2026-13-01", "2026-02-30", "2025-02-29", "24-10-2026", "2026/10/24", "", None, "abc"]:
            with self.subTest(text=text):
                self.assertIsNone(parse_date(text))


class TransactionTests(unittest.TestCase):
    def test_valid_expense(self):
        data, errors = validate_transaction("2026-10-24", "expense", "250.75", EXPENSE_CAT, "  Vegetables ")
        self.assertEqual(errors, [])
        self.assertEqual(data["amount"], Decimal("250.75"))
        self.assertEqual(data["category_id"], 5)
        self.assertEqual(data["description"], "Vegetables")

    def test_valid_income(self):
        _, errors = validate_transaction("2026-10-01", "income", "60000", INCOME_CAT)
        self.assertEqual(errors, [])

    def test_category_must_match_type(self):
        _, errors = validate_transaction("2026-10-24", "expense", "10", INCOME_CAT)
        self.assertEqual(len(errors), 1)
        self.assertIn("not an expense category", errors[0])

    def test_missing_category(self):
        _, errors = validate_transaction("2026-10-24", "expense", "10", None)
        self.assertIn("Choose a valid category.", errors)

    def test_bad_type(self):
        _, errors = validate_transaction("2026-10-24", "gift", "10", EXPENSE_CAT)
        self.assertIn("Choose income or expense.", errors)

    def test_several_errors_reported_together(self):
        data, errors = validate_transaction("bad", "expense", "-5", None)
        self.assertEqual(len(errors), 3)
        self.assertEqual(data["amount"], "-5")  # raw text kept so the form can show it again

    def test_year_range_boundaries(self):
        for date_text, ok in [("2000-01-01", True), ("2100-12-31", True),
                              ("1999-12-31", False), ("2101-01-01", False)]:
            with self.subTest(date=date_text):
                _, errors = validate_transaction(date_text, "expense", "10", EXPENSE_CAT)
                self.assertEqual(errors == [], ok)

    def test_description_is_cut_to_255_characters(self):
        data, _ = validate_transaction("2026-10-24", "expense", "10", EXPENSE_CAT, "x" * 300)
        self.assertEqual(len(data["description"]), 255)

    def test_missing_description_is_allowed(self):
        data, errors = validate_transaction("2026-10-24", "expense", "10", EXPENSE_CAT, None)
        self.assertEqual(errors, [])
        self.assertEqual(data["description"], "")


if __name__ == "__main__":
    unittest.main()
