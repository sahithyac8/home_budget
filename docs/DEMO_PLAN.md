# D8. Final Demonstration Plan (target 10 minutes; allowed 8 to 12)

The Expo asks for a live demonstration of the problem, the working application, database records, analysis,
charts, test results and conclusions. Each member therefore speaks for about 1 minute on the slide and then
shows their part live, instead of speaking only from the slides.

## Timeline
| Time | Who | Slide | Show live |
|---|---|---|---|
| 0:00 to 1:00 | Member 1 | Introduction | The problem and the five parts of the system |
| 1:00 to 2:30 | Member 1 (Frontend) | Frontend | Open the Dashboard; add one expense on the Add form (show the category list change with the type); show the Budgets page |
| 2:30 to 4:00 | Member 2 (Backend) | Backend | Submit a bad amount (-5) to show the error message; open `/health`; import `sample_import.csv` and show the 6 rejected rows with reasons; click Export CSV |
| 4:00 to 5:30 | Member 3 (Database) | Database | In MySQL: `SHOW TABLES;`, `SELECT * FROM transactions ORDER BY transaction_date DESC LIMIT 5;`, show the ER diagram; try deleting a category that is in use |
| 5:30 to 7:00 | Member 4 (Analysis) | Data analysis | Dashboard for Oct 2026: totals, the Over list, the Smart insights; Budgets for Nov 2026: Suggested limits and "Pre-fill" |
| 7:00 to 8:30 | Member 5 (Visualization) | Visualization | Reports page: the four charts and their captions; month-wise table with the August deficit |
| 8:30 to 9:30 | Member 5 | Test results | Run `python -m unittest discover -v` (123 pass); show `docs/TEST_REPORT.md` |
| 9:30 to 10:00 | All | Conclusion | Acceptance criteria met; limitations; future work; thank you |

Shorten the slide scripts in `Presentation Script` to about 60 seconds each; the live demonstration replaces the rest.

## Pre-demonstration checklist (Expo requirements)
- [ ] MySQL is running; `schema.sql` and `sample_data.sql` loaded on the demonstration machine (manual checks M1 to M8 in `TEST_REPORT.md` done).
- [ ] Credentials are set with environment variables (`MYSQL_*`); no password appears in any file or screen.
- [ ] `python app.py` starts and `/health` shows `ok`. Debug mode is off.
- [ ] Browser tabs ready: Dashboard (`?year=2026&month=10`), Add form, Budgets (`?year=2026&month=11`), Reports (`?year=2026&month=10`), Import page, MySQL terminal.
- [ ] `sample_import.csv` is easy to find. After the demo delete the imported November rows (query in `TEST_REPORT.md`).
- [ ] Submit: source code, `schema.sql` and `sample_data.sql`, README, final report, charts, presentation.
- [ ] Everyone can answer questions on their part (see the list below).

## Questions the team should be ready for
| Topic | Question | Short answer |
|---|---|---|
| Schema | Why three tables? | Categories are reused by transactions and budgets, which avoids repeating names and lets us enforce rules with foreign keys |
| Schema | Why DECIMAL and not float? | Floats cause rounding errors; DECIMAL(12,2) keeps exact two-decimal money |
| Routes | How is a request handled? | Route, then `db.py` for data, then `analysis.py` for calculation, then a template or a chart |
| Data cleaning | How do you keep data clean? | Server validation, database CHECK and FOREIGN KEY constraints, CSV import report |
| Formulas | How is savings or Over decided? | Savings = income - expenses; Over = spent > budget; Warning = 80% or more used |
| Testing | What did you test? | 123 automated tests for normal, invalid, empty, boundary and database-error cases, plus manual MySQL checks |
| Login | How are accounts and passwords handled? | Sign up and log in in `auth.py`; passwords stored only as salted hashes; every query filters by `user_id`; pages are private by default |
| Division of work | Who built what? | See the team table in `PROPOSAL.md` |
