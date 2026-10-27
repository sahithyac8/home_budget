# Home Budget (Expense Tracker) and Analysis System

A Flask + MySQL web application for recording household income and expenses, setting monthly
category budgets, and analysing spending with Pandas, NumPy and Matplotlib.
Data is entered manually; there is no bank or payment integration (by design, see the project brief).

> Educational project. All sample data is synthetic. No real banking details are stored.

## 1. Quick start

Requirements: Python 3.10+, MySQL 8.0.16+ (needed for CHECK constraints).

```bash
pip install -r requirements.txt

# 1. Create the database, tables and the 12 default categories
mysql -u root -p < schema.sql
# 2. Optional demo data (Aug-Oct 2026, includes edge cases)
mysql -u root -p home_budget < sample_data.sql

# 3. Set credentials through environment variables (nothing is hard-coded). See .env.example
export MYSQL_HOST=localhost MYSQL_USER=root MYSQL_PASSWORD='your-password' MYSQL_DB=home_budget
export SECRET_KEY='any-long-random-text'
# Windows PowerShell:  $env:MYSQL_PASSWORD = "your-password"

# 4. Run
python app.py            # open http://127.0.0.1:5000   (health check: http://127.0.0.1:5000/health)
```

Run the tests (no MySQL needed): `python -m unittest discover -v`  (91 tests, see `docs/TEST_REPORT.md`).

## 2. Features

Core features from the project brief:

| Brief requirement | Where it is |
|---|---|
| Add, view, update, delete income and expense records | **Transactions** page (`/transactions`) |
| Categorise (groceries, rent, transport, healthcare, education, entertainment...) | **Categories** page, 12 defaults in `schema.sql` |
| Total income, total expenses, monthly savings | **Dashboard** cards and **Reports** month-wise table |
| Monthly spending limit per category | **Budgets** page |
| Category-wise and month-wise summaries | **Reports** page (category table, month table, category-by-month table) |
| Identify categories over budget | Red alert box on the Dashboard, **Budget violations** table in Reports, status column on Budgets |
| Charts comparing categories and months | 4 Matplotlib charts, each with title, axes, units and a "How to read this chart" caption |

Three additional features (small, and each can be explained in under a minute):

1. **Smart insights** (`analysis.insights`): turns the numbers into plain sentences, for example
   *"Spending is up 37.1% compared with Sep 2026"* and *"Entertainment is 30% over its budget"*.
   Shown on the Dashboard and Reports and at `/api/insights`. Each sentence comes from one simple rule on
   numbers that are already calculated. This answers the Expo requirement to explain metrics in plain language.
2. **CSV export and import with a validation report** (`csv_io.py`, route `/import`):
   export transactions or the monthly summary for Excel; import a CSV where every row is checked with the same
   rules as the Add form. Valid rows are saved in one database transaction, invalid rows are listed with the
   reason (shown with `sample_import.csv`, which has 6 good and 6 deliberately bad rows). Uses only Python's
   built-in `csv` module, so no extra library is needed (the brief allows an optional library for export, we did not need one).
   Exported text cells that start with `= + - @` get a leading apostrophe to prevent spreadsheet formula injection.
3. **Budget suggestions** (`analysis.budget_suggestions`): on the Budgets page, suggests a limit for each category =
   average spending over the previous 3 months that have expenses, rounded up to the next 100. "Pre-fill the
   form" fills the inputs but saves nothing until the user presses Save.

**Is a login page needed?** No. The brief and the deliverables list ask for user roles only "if applicable"; this
is a single-household tool with manually entered data, so we documented it as an assumption (see
`docs/PROPOSAL.md`). Authentication is listed under future work.

## 3. Project structure

```
app.py            Flask routes, error handlers, health check, JSON API
validation.py     Input rules shared by the forms and the CSV import
csv_io.py         CSV export and import (feature 2)
db.py             PyMySQL helpers: query_all, query_one, execute, execute_many (commit / rollback)
analysis.py       Pandas/NumPy: summaries, category analysis, budget status, savings report,
                  insights (feature 1), budget suggestions (feature 3)
charts.py         Matplotlib charts returned as PNG
config.py         Settings read from environment variables
schema.sql        D2: tables, keys, constraints, default categories
sample_data.sql   Sample dataset incl. edge cases
sample_import.csv Demo file for the CSV import (6 valid, 6 invalid rows)
templates/        Jinja pages        static/  stylesheet
tests/            91 unittest cases  docs/    documentation, ER diagram, screenshots, test evidence
```

## 4. Routes and API endpoint list

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Dashboard for a month (`?year=&month=`) |
| GET | `/transactions` | List with filters (`type`, `category`, `month=YYYY-MM`) |
| GET, POST | `/transactions/add` | Create (validated) |
| GET, POST | `/transactions/<id>/edit` | Update (404 if the id does not exist) |
| POST | `/transactions/<id>/delete` | Delete |
| GET, POST | `/categories` | List, add |
| POST | `/categories/<id>/delete` | Delete (blocked when the category has transactions) |
| GET, POST | `/budgets` | Set monthly limits, view utilization and suggestions (`?suggest=1` pre-fills) |
| GET | `/reports` | Month-wise, category-wise, savings and violation reports |
| GET | `/chart/<name>.png` | `distribution`, `monthly`, `budget`, `category_month` |
| GET | `/export/transactions.csv` | CSV download (`?year=&month=` optional) |
| GET | `/export/monthly-summary.csv` | CSV download (`?year=`) |
| GET, POST | `/import` | Upload a CSV, see the validation report |
| GET | `/health` | `{"status":"ok","database":"up"}` or HTTP 503 when MySQL is unreachable |
| GET | `/api/transactions` | JSON list of all transactions |
| GET | `/api/summary` | JSON totals and the 12-month summary (`?year=&month=`) |
| GET | `/api/budget-status` | JSON budget status per category (`?year=&month=`) |
| GET | `/api/insights` | JSON list of insight sentences |

Error handling: invalid form input returns HTTP 400 and shows the form again with the messages and the
user's values; unknown pages give a friendly 404; uploads over 1 MB give 413; any MySQL error gives a
friendly 503 page and is logged; every write is committed or rolled back as a unit (`db.py`).

## 5. Database schema (summary)

Three tables as suggested in the brief. Full column list and rules: `docs/DATA_DICTIONARY.md`; diagram: `docs/er_diagram.png`.

- `categories(category_id PK, category_name, category_type)`; unique on (name, type)
- `transactions(transaction_id PK, transaction_date, transaction_type, category_id FK, amount DECIMAL(12,2) > 0, description)`; `ON DELETE RESTRICT`
- `monthly_budgets(budget_id PK, category_id FK, budget_month 1-12, budget_year, budget_amount > 0)`; unique on (category, month, year); `ON DELETE CASCADE`

## 6. Analysis methodology

Formulas, filters, assumptions, summary tables and chart interpretations are in `docs/ANALYSIS_METHODOLOGY.md`. In short:
savings = income - expenses; savings rate = savings / income x 100 (0 when income is 0); a category is **Over**
when spent > budget, **Warning** from 80% used, otherwise **OK**.

## 7. Screenshots

| | |
|---|---|
| Dashboard | `docs/screenshots/01_dashboard.png` |
| Transactions | `docs/screenshots/02_transactions.png` |
| Add form | `docs/screenshots/03_add_transaction.png` |
| Budgets with suggestions | `docs/screenshots/04_budgets_with_suggestions.png` |
| Reports | `docs/screenshots/05_reports.png` |
| Categories | `docs/screenshots/06_categories.png` |
| CSV import result | `docs/screenshots/07_csv_import_result.png` |

## 8. Limitations

- Single household, no login or user accounts; anyone who can open the site can see and change the data.
- Manual data entry only; no bank, payment or SMS integration.
- Descriptive analysis only (no forecasting). Budget suggestions are plain averages and need at least one earlier month with expenses.
- One currency (set with the `CURRENCY` variable). Amounts are limited to 9,999,999,999.99.
- CSV import accepts UTF-8 files of up to 1000 rows and 1 MB, and does not create new categories.
- Statistics are descriptive: results are educational and are not financial advice.

## 9. Where each standard deliverable is

See `docs/DELIVERABLES_CHECKLIST.md` (D1 to D8 and the Expo checklist, mapped to files).
