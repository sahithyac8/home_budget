# D6. Test Plan and Test Report

## 1. How to run
```bash
python -m unittest discover -v        # 91 tests, about 2 seconds, no MySQL server needed
```
The automated tests replace MySQL with `tests/helpers.py::FakeDB`, an in-memory copy of `sample_data.sql`,
so they run anywhere and test the application's own logic. Section 4 lists the manual checks to run once
against the real MySQL server before the demonstration.

**Result of the last run: 91 tests, 91 passed, 0 failed.** Full output: `docs/test_results.txt`.

| Test file | Tests | Covers |
|---|---|---|
| `tests/test_validation.py` | 13 | Amount, date and transaction rules |
| `tests/test_analysis.py` | 19 | Totals, savings, category analysis, budget status, insights, suggestions, charts |
| `tests/test_csv_io.py` | 15 | CSV export, formula-injection guard, import validation |
| `tests/test_routes.py` | 44 | Pages, CRUD, categories, budgets, API, health, export/import, empty and failing database |

## 2. Test cases by type (examples; every test name is in `test_results.txt`)
| Type | Example cases | Expected result | Result |
|---|---|---|---|
| Normal input | Add expense 250.75; edit; delete; October totals 61,500 / 34,400 / 27,100; 3 categories Over | Saved or calculated exactly | Pass |
| Invalid input | Amount -5, 0, "abc", 1.999, NaN; date 2026-02-30; income category on an expense; unknown category; type "gift" | HTTP 400, form shown again with messages, nothing written | Pass |
| Empty dataset | No transactions and no budgets: every page, chart, export and API endpoint | Pages load, totals 0, charts show "No data", export has headers only | Pass |
| Boundary values | Amount 0.01 and 9,999,999,999.99 accepted; 10,000,000,000 rejected; years 2000 and 2100 accepted, 1999 and 2101 rejected; spending exactly 100% of budget is Warning not Over; exactly 80% is Warning; 0% spent is OK; exactly 1000 CSV rows accepted, 1001 rejected; leap day 2024-02-29 | As described | Pass |
| Database errors | MySQL unreachable (`/health`, every page, a write, a CSV import); duplicate category; deleting a category that has transactions | HTTP 503 with a friendly page, or a clear message; no stack trace | Pass |
| Data quality (import) | `sample_import.csv`: 6 valid rows saved, 6 rejected with reasons; wrong columns; empty file; non-UTF-8 file; file over 1 MB | Valid rows saved only; clear error for bad files | Pass |
| Security | Formula injection in exported text (`=`, `+`, `@`) | Prefixed with an apostrophe | Pass |

## 3. Defect found and fixed during testing
Importing a row such as `income, Rent` (a category name that exists only under the other type) first showed the
generic message "Choose a valid category". The lookup in `csv_io.parse_import` now finds the category by name and
the validator reports "Category 'Rent' is not an income category." A test (`test_sample_file_has_six_valid_and_six_rejected_rows`) covers it.

## 4. Manual checks against the real MySQL server (fill in before the demonstration)
| # | Step | Expected | Result (Pass / Fail) | Date, tester |
|---|---|---|---|---|
| M1 | `mysql -u root -p < schema.sql` then `sample_data.sql` | No errors; `SELECT COUNT(*) FROM transactions;` returns 15 | | |
| M2 | Start the app, open `/health` | `{"status":"ok","database":"up"}` | | |
| M3 | Dashboard for Oct 2026 | Income 61,500.00, expenses 34,400.00, savings 27,100.00; 3 violations | | |
| M4 | Add, edit and delete a transaction; check the row in MySQL each time | Row appears, changes, disappears | | |
| M5 | Try to delete the Groceries category | Message: cannot delete a category that has transactions | | |
| M6 | Import `sample_import.csv`; then `SELECT COUNT(*)` | 6 new rows (21 total); 6 rejected rows listed | | |
| M7 | Stop MySQL and reload any page | Friendly "Database unavailable" page; `/health` returns 503 | | |
| M8 | Start MySQL again and reload | Application works again without restarting | | |

Delete the imported November rows afterwards (`DELETE FROM transactions WHERE transaction_date >= '2026-11-01';`) so the demonstration numbers stay as documented.

## 5. Limitations of the testing
- Automated tests use an in-memory stand-in for MySQL, so MySQL-specific behaviour (CHECK constraints, foreign key errors, `ON DUPLICATE KEY UPDATE`) is covered by manual steps M1 to M8, not by the automated suite.
- No browser-automation tests; the screenshots in `docs/screenshots/` show the pages visually.
