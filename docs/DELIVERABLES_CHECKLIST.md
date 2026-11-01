# Alignment with the Standard Deliverables and the Expo Checklist

Status: **Done** = in this folder and checked. **Team to do** = needs your names, your machine or your own words.

| # | Requirement | Where | Status |
|---|---|---|---|
| D1 | Title, problem statement, objectives, scope, user roles, features, assumptions, project plan | `docs/PROPOSAL.md` | Done; fill in member names |
| D2 | ER diagram, schema, primary/foreign keys, sample data, SQL setup script, data dictionary | `docs/er_diagram.png`, `docs/DATA_DICTIONARY.md`, `schema.sql`, `sample_data.sql` | Done |
| D3 | Working application, CRUD, validation, error handling, database connectivity | `app.py`, `validation.py`, `db.py`; 400/404/413/503 handling; `/health`; JSON API | Done; run against your MySQL (M1 to M8) |
| D4 | Pandas/NumPy analysis with formulas, filters, assumptions, summary tables | `analysis.py`, `docs/ANALYSIS_METHODOLOGY.md` | Done |
| D5 | At least 3 charts, each with title, axes, units and interpretation | 4 charts in `charts.py`; captions in `templates/_macros.html`; interpretations in `docs/ANALYSIS_METHODOLOGY.md` | Done |
| D6 | Tests: normal, invalid, empty, boundary, database errors, with evidence | `tests/` (123 tests), `docs/TEST_REPORT.md`, `docs/test_results.txt` | Done; complete manual table M1 to M8 |
| D7 | README setup, synopsis, API list, schema, methodology, screenshots, limitations | `README.md`, `docs/PROPOSAL.md`, `docs/screenshots/` | Done; retake screenshots from your own MySQL run if you can |
| D8 | 8 to 12 minute demonstration | `docs/DEMO_PLAN.md`; slides and speaking script | Done; rehearse once with a timer |
| Final | Final report | Combine `PROPOSAL.md`, `DATA_DICTIONARY.md`, `ANALYSIS_METHODOLOGY.md`, `TEST_REPORT.md` and the screenshots into one document | Team to do |

## Expo checklist
| Requirement | Status |
|---|---|
| Submit source code, SQL schema/seed script, README and final report | Files ready; final report to compile |
| Application starts and connects using environment-based credentials | Done (`config.py`, `.env.example`); verify on the demo machine |
| At least one end-to-end use case with its analysis and chart | Add a transaction, then see totals, insights and charts update (`DEMO_PLAN.md`) |
| Charts and metrics explained in plain language, including definitions and limitations | Chart captions, Smart insights, `ANALYSIS_METHODOLOGY.md` |
| Team can answer questions on schema, routes, data cleaning, formulas, testing, work division | Question table in `DEMO_PLAN.md` |
| Synthetic data; no passwords or real banking details | Done: all data is synthetic; no secrets in the code |

## General implementation notes
| Note | Status |
|---|---|
| Schema is a starting point; adapt it | Same three tables as suggested, with constraints added |
| Enough sample data including edge cases and missing/invalid data | Aug (no income, NULL description, 100% and 80% boundaries), Sep, Oct; `sample_import.csv` with invalid rows |
| No hard-coded credentials | Environment variables; `.env.example`; `.gitignore` excludes `.env` |
| Core stack is sufficient | Yes; CSV uses the standard library; tests use the standard `unittest` |
| Forecasting needs method, limitations and a baseline | No forecasting is claimed; budget suggestions are a plain average and the limitation is stated |
| Label outputs as educational | README and methodology state this |
