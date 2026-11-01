# Home Budget (Expense Tracker) and Analysis System

A Flask + MySQL web application for recording household income and expenses, setting monthly
category budgets, and analysing spending with Pandas, NumPy and Matplotlib.
Data is entered manually; there is no bank or payment integration (by design, see the project brief).

> Educational project. All sample data is synthetic. No real banking details are stored.

## 1. Quick start

Requirements: Python 3.10+, MySQL 8.0.16+ (needed for CHECK constraints).

```bash
pip install -r requirements.txt

# 1. Put your settings in a file called .env (copy .env.example). It is never uploaded to GitHub.
#    MYSQL_PASSWORD=your-password   SECRET_KEY=any-long-random-text

# 2. Create the tables, plus (optional) a demo account with Aug-Oct 2026 data
python init_db.py --demo      # demo login: demo@example.com / Demo@1234
#    (the same thing with the mysql command line:  mysql -u root -p < schema.sql  and  sample_data.sql)

# 3. Run
python app.py            # open http://127.0.0.1:5000   (health check: http://127.0.0.1:5000/health)
```

Open the site, press **Sign up** to create your own account, or log in with the demo account.
Putting the site on the internet for free: see `docs/DEPLOYMENT.md`.

Run the tests (no MySQL needed): `python -m unittest discover -v`  (123 tests, see `docs/TEST_REPORT.md`).

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

**Accounts (added after the first version).** A public landing page leads to **Sign up** and **Log in**
(`auth.py`). Passwords are stored only as salted PBKDF2 hashes. Every record (transactions, categories, budgets)
carries a `user_id`, every query filters by it, and every page except the landing, login and sign-up pages is
private by default (`before_request` in `app.py`). Each new user receives their own 12 default categories.

## 3. Project structure

```
app.py            Flask routes, login gate, error handlers, health check, JSON API
auth.py           Sign up, log in, log out (a Flask Blueprint), password hashing
validation.py     Input rules shared by the forms, the sign-up form and the CSV import
init_db.py        Creates the tables (and demo data) from Python; works locally and on a hosted MySQL
csv_io.py         CSV export and import (feature 2)
db.py             PyMySQL helpers: query_all, query_one, execute, execute_many (commit / rollback)
analysis.py       Pandas/NumPy: summaries, category analysis, budget status, savings report,
                  insights (feature 1), budget suggestions (feature 3)
charts.py         Matplotlib charts returned as PNG
config.py         Settings read from environment variables
schema.sql        D2: tables, keys, constraints, default categories
sample_data.sql   Sample dataset incl. edge cases
sample_import.csv Demo file for the CSV import (6 valid, 6 invalid rows)
templates/        Jinja pages (landing, login, sign up, app pages)        static/  stylesheet (theme)
tests/            123 unittest cases  docs/    documentation, ER diagram, screenshots, test evidence
```

## 4. Routes and API endpoint list

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Public landing page (logged-in users go to the dashboard) |
| GET, POST | `/register`, `/login` | Create an account, log in (public) |
| POST | `/logout` | Log out |
| GET | `/dashboard` | Dashboard for a month (`?year=&month=`) |
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

The three tables suggested in the brief, plus `users`. Full column list and rules: `docs/DATA_DICTIONARY.md`; diagram: `docs/er_diagram.png`.

- `users(user_id PK, full_name, email UNIQUE, password_hash, created_at)`
- `categories(category_id PK, user_id FK, category_name, category_type)`; unique on (user, name, type)
- `transactions(transaction_id PK, user_id FK, transaction_date, transaction_type, category_id FK, amount DECIMAL(12,2) > 0, description)`; `ON DELETE RESTRICT` on the category
- `monthly_budgets(budget_id PK, user_id FK, category_id FK, budget_month 1-12, budget_year, budget_amount > 0)`; unique on (user, category, month, year); `ON DELETE CASCADE`

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

- Accounts are basic: no password reset, no email verification and no "delete my account"; wrong passwords are limited to 5 tries per email (counted in memory, so a restart resets the count). Categories are per user, so they are not shared.
- Manual data entry only; no bank, payment or SMS integration.
- Descriptive analysis only (no forecasting). Budget suggestions are plain averages and need at least one earlier month with expenses.
- One currency (set with the `CURRENCY` variable). Amounts are limited to 9,999,999,999.99.
- CSV import accepts UTF-8 files of up to 1000 rows and 1 MB, and does not create new categories.
- Statistics are descriptive: results are educational and are not financial advice.

## 9. Where each standard deliverable is

See `docs/DELIVERABLES_CHECKLIST.md` (D1 to D8 and the Expo checklist, mapped to files).
