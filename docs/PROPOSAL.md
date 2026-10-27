# D1. Project Proposal and Requirements

## Title
Home Budget (Expense Tracker) and Analysis System

## Problem statement
Households earn and spend every month without a clear picture of where the money goes. Overspending is
noticed only after the month is over, and spreadsheets are easy to break and hard to analyse. A simple web
application that records transactions, enforces monthly category limits and explains spending patterns
helps people make informed financial decisions.

## Objectives
1. Record and manage household income and expense transactions (create, view, update, delete).
2. Categorise transactions and let the user set monthly spending limits per expense category.
3. Calculate total income, total expenses and monthly savings accurately.
4. Produce category-wise and month-wise summaries and identify categories that exceed their budget.
5. Present the results as clear charts and plain-language insights.
6. Store all data in MySQL, with validation and error handling that protect data quality.

## Scope
In scope: transaction management, expense categorisation, monthly budget tracking, descriptive analysis
(Pandas, NumPy), visualisation (Matplotlib), CSV import/export, read-only JSON API.

Out of scope (as stated in the brief): bank integration, payment gateways, real-time sync, forecasting models.

## User roles
One role: the household member who enters and reviews the data. **No login or registration is included.**
The brief and the deliverables list ask for user roles only "if applicable"; with one household and manually
entered data there is nothing to separate. Multi-user accounts are recorded as future work.

## Features
Core (from the brief): transaction CRUD; categories; totals and savings; monthly budgets; category-wise and
month-wise summaries; budget-violation detection; charts.
Additional: (1) smart insights, (2) CSV export and import with a validation report, (3) budget suggestions.
Supporting: health check, JSON API, friendly error pages, 91 automated tests.

## Technology
Python 3, Flask, MySQL 8, PyMySQL, Pandas, NumPy, Matplotlib (core stack only; no extra libraries).
Credentials come from environment variables; `.env` files are excluded from version control.

## Assumptions
- Amounts are in one currency (default rupee) and have at most two decimals.
- A budget belongs to one expense category for one month and year; income categories have no budget.
- Data is synthetic or entered by the user; no personal banking data is stored.
- The household uses the application on one machine or a trusted network (no authentication).

## Project plan and deadlines
| Week | Dates | Work | Evidence |
|---|---|---|---|
| 1, first review | 21-10-2026 to 23-10-2026 | Synopsis and scope; ER diagram, `schema.sql`, `sample_data.sql`, data dictionary; app structure, DB connection, health check, CRUD routes, validation and error handling | `docs/PROPOSAL.md`, `docs/DATA_DICTIONARY.md`, `schema.sql`, `app.py` |
| 2, final submission | 28-10-2026 to 30-10-2026 | Pandas/NumPy analysis and formulas; Matplotlib charts with interpretation; end-to-end run; test report; README; API list; demonstration plan | `analysis.py`, `charts.py`, `docs/ANALYSIS_METHODOLOGY.md`, `docs/TEST_REPORT.md`, `README.md`, `docs/DEMO_PLAN.md` |

## Team responsibilities
| Member | Role | Main files |
|---|---|---|
| [Member 1] | Frontend | `templates/`, `static/style.css` |
| [Member 2] | Backend | `app.py`, `validation.py`, `csv_io.py`, `db.py` |
| [Member 3] | Database | `schema.sql`, `sample_data.sql`, `docs/DATA_DICTIONARY.md` |
| [Member 4] | Data analysis | `analysis.py`, `docs/ANALYSIS_METHODOLOGY.md` |
| [Member 5] | Visualization and testing | `charts.py`, `tests/`, `docs/TEST_REPORT.md` |

## Risks and mitigation
| Risk | Mitigation |
|---|---|
| Wrong money totals from rounding | `DECIMAL(12,2)` in MySQL and `Decimal` in Python; tests check totals by hand |
| Invalid or missing data | Server-side validation, CHECK constraints, CSV validation report, edge-case sample data |
| MySQL not running at the demonstration | `/health` check and a friendly 503 page; run the pre-demo checklist in `docs/DEMO_PLAN.md` |
| Credentials leaking | Environment variables only; `.gitignore` excludes `.env` |
