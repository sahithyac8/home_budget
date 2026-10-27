"""D6: CSV export and import (feature 2) - normal rows, invalid rows, bad files."""
import unittest
from pathlib import Path

import csv_io
import analysis
from tests.helpers import CATEGORIES, TRANSACTIONS

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "sample_import.csv"
HEADER = "transaction_date,transaction_type,category,amount,description\n"


class ExportTests(unittest.TestCase):
    def test_transactions_export(self):
        lines = csv_io.transactions_to_csv(TRANSACTIONS).splitlines()
        self.assertEqual(lines[0], "transaction_date,transaction_type,category,amount,description")
        self.assertEqual(len(lines), 1 + len(TRANSACTIONS))
        self.assertIn("2026-10-20,expense,Entertainment,3900.00,Weekend trip", lines)

    def test_missing_description_exports_as_empty(self):
        self.assertIn("2026-08-14,expense,Utilities,2000.00,", csv_io.transactions_to_csv(TRANSACTIONS).splitlines())

    def test_formula_injection_is_neutralised(self):
        rows = [dict(TRANSACTIONS[0], description="=HYPERLINK(\"http://x\")"),
                dict(TRANSACTIONS[1], description="+1"), dict(TRANSACTIONS[2], description="@cmd")]
        out = csv_io.transactions_to_csv(rows)
        self.assertNotIn(',=HYPERLINK', out)
        self.assertIn("'=HYPERLINK", out)
        self.assertIn("'+1", out)
        self.assertIn("'@cmd", out)

    def test_summary_export(self):
        summary = analysis.monthly_summary(analysis.transactions_df(TRANSACTIONS), 2026)
        lines = csv_io.summary_to_csv(summary).splitlines()
        self.assertEqual(lines[0], "month,income,expense,savings,savings_rate_percent")
        self.assertEqual(len(lines), 13)
        self.assertIn("Oct,61500.00,34400.00,27100.00,44.1", lines)


class ImportTests(unittest.TestCase):
    def parse(self, text):
        return csv_io.parse_import(text, CATEGORIES)

    def test_sample_file_has_six_valid_and_six_rejected_rows(self):
        valid, rejected, fatal = self.parse(SAMPLE_CSV.read_text(encoding="utf-8"))
        self.assertIsNone(fatal)
        self.assertEqual(len(valid), 6)
        self.assertEqual([r["row"] for r in rejected], [8, 9, 10, 11, 12, 13])
        reasons = " | ".join(" ".join(r["errors"]) for r in rejected)
        for expected in ["valid date", "greater than 0", "at most 2 decimal", "valid category", "not an income category"]:
            self.assertIn(expected, reasons)

    def test_valid_rows_are_ready_to_insert(self):
        valid, _, _ = self.parse(HEADER + "2026-11-02,Expense,groceries,450.50,Vegetables\n")
        self.assertEqual(valid[0]["category_id"], 5)  # names are matched without case
        self.assertEqual(str(valid[0]["amount"]), "450.50")

    def test_boundary_amounts(self):
        valid, rejected, _ = self.parse(HEADER + "2026-11-02,expense,Groceries,0.01,a\n"
                                                 "2026-11-02,expense,Groceries,9999999999.99,b\n"
                                                 "2026-11-02,expense,Groceries,10000000000,c\n"
                                                 "2026-11-02,expense,Groceries,0,d\n")
        self.assertEqual(len(valid), 2)
        self.assertEqual(len(rejected), 2)

    def test_blank_lines_are_skipped_and_description_is_optional(self):
        text = "transaction_date,transaction_type,category,amount\n\n2026-11-02,expense,Groceries,10\n\n"
        valid, rejected, fatal = self.parse(text)
        self.assertEqual((len(valid), len(rejected), fatal), (1, 0, None))

    def test_headers_are_case_and_space_insensitive(self):
        valid, _, fatal = self.parse(" Transaction_Date , TRANSACTION_TYPE ,Category,Amount\n2026-11-02,expense,Rent,100\n")
        self.assertIsNone(fatal)
        self.assertEqual(len(valid), 1)

    def test_short_row_is_rejected_not_crashing(self):
        valid, rejected, _ = self.parse(HEADER + "2026-11-02,expense\n")
        self.assertEqual((len(valid), len(rejected)), (0, 1))

    def test_empty_file(self):
        self.assertEqual(self.parse("")[2], "The file is empty.")

    def test_missing_required_column(self):
        fatal = self.parse("transaction_date,category,amount\n2026-11-02,Rent,100\n")[2]
        self.assertIn("transaction_type", fatal)

    def test_header_only_file_imports_nothing(self):
        self.assertEqual(self.parse(HEADER)[:3], ([], [], None))

    def test_too_many_rows(self):
        body = "2026-11-02,expense,Groceries,1,x\n" * (csv_io.MAX_IMPORT_ROWS + 1)
        self.assertIn("Too many rows", self.parse(HEADER + body)[2])

    def test_exactly_the_maximum_number_of_rows_is_accepted(self):
        body = "2026-11-02,expense,Groceries,1,x\n" * csv_io.MAX_IMPORT_ROWS
        valid, _, fatal = self.parse(HEADER + body)
        self.assertEqual((len(valid), fatal), (csv_io.MAX_IMPORT_ROWS, None))


if __name__ == "__main__":
    unittest.main()
