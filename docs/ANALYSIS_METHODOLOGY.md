# D4 and D5. Analysis Methodology, Formulas and Chart Interpretation

All functions are in `analysis.py` (Pandas/NumPy) and `charts.py` (Matplotlib). They take plain data and return
DataFrames, so each can be run and tested without the web application.

## 1. Data preparation
1. Transactions are read from MySQL as dictionaries and loaded into a DataFrame (`transactions_df`).
2. `amount` is converted from Decimal to float for calculation; `transaction_date` becomes a datetime; `year` and `month` columns are added.
3. Validation has already guaranteed positive amounts, valid dates and matching category types, so no rows need to be dropped (see `validation.py` and the constraints in `schema.sql`).

## 2. Formulas
| Result | Formula | Where |
|---|---|---|
| Total income / expenses | sum of `amount` for rows of that type in the period | `period_totals` |
| Monthly savings | income - expenses | `monthly_summary`, `period_totals` |
| Savings rate (%) | savings / income x 100; **0 when income is 0** | `_safe_pct` (`np.divide` with `where=den>0`) |
| Category share (%) | category expense / total expense x 100, rounded to 1 decimal | `category_expense` |
| Budget used (%) | spent / budget x 100 | `budget_status` |
| Remaining | budget - spent | `budget_status` |
| Over by | max(spent - budget, 0) (`np.maximum`) | `budget_status` |
| Best / worst month | `np.argmax` / `np.argmin` of monthly savings over months that have data | `savings_report` |
| Suggested budget | mean of the category's monthly spending over the previous 3 months that have expenses, rounded up to the next 100 (`np.ceil`) | `budget_suggestions` |
| Spending change vs previous month (%) | (this month - previous month) / previous month x 100 | `insights` |

**Status rule** (`np.where`): **Over** if spent > budget; **Warning** if budget used >= 80%; otherwise **OK**.
Spending exactly equal to the budget is therefore Warning, not Over.

## 3. Filters
- Period: by year, and by month (month 0 means the whole year).
- Type: income or expense (category analysis uses expenses only).
- Budget status uses only the budgets stored for the chosen month and year.
- Budget suggestions use the three calendar months before the chosen month; months with no expense records are skipped so that an empty month does not lower the average.

## 4. Assumptions
- Every transaction belongs to exactly one category and one date; transfers between accounts are not modelled.
- A month with no income has savings rate 0% (not undefined) so tables and charts stay readable.
- Budgets exist only for expense categories and are set by the user; a category without a budget is not checked.
- All amounts are in one currency, so no conversion is needed.

## 5. Summary tables (sample data, October 2026)
| Measure | Value |
|---|---|
| Income | 61,500.00 |
| Expenses | 34,400.00 |
| Savings | 27,100.00 (44.1% of income) |
| Largest expense | Rent 15,000.00 (43.6%) |
| Spending vs September | +37.1% (25,100.00 to 34,400.00) |

| Category | Budget | Spent | Used | Status |
|---|---|---|---|---|
| Entertainment | 3,000.00 | 3,900.00 | 130.0% | Over (by 900.00) |
| Groceries | 7,000.00 | 7,800.00 | 111.4% | Over (by 800.00) |
| Healthcare | 3,000.00 | 3,200.00 | 106.7% | Over (by 200.00) |
| Rent | 15,000.00 | 15,000.00 | 100.0% | Warning |
| Education | 5,000.00 | 4,500.00 | 90.0% | Warning |

These numbers are checked by hand in `tests/test_analysis.py`.

## 6. Charts (all have a title, labelled axes with units, and a caption on the page)
| Chart | Shows | How to interpret it (sample data) |
|---|---|---|
| Expense distribution (pie) | Share of each category in the period's expenses; legend gives percent | Rent is the largest slice (43.6%), so housing dominates October spending |
| Monthly income vs expenses (bars + line; y: amount in rupees, x: month) | Income, expenses and savings for each month | Aug is below zero (expenses but no income); Sep and Oct are positive, so the household saved in both |
| Budget utilization (horizontal bars; x: percent of budget used, dashed line at 100%) | How much of each monthly limit is used | Entertainment, Groceries and Healthcare cross the 100% line (red); Rent and Education are orange (80% or more) |
| Expenses by category and month (stacked bars; y: amount in rupees) | Month-by-month spending split by category | Rent is a steady block each month; the October rise comes from Groceries, Healthcare, Education and Entertainment |

Colour is never the only signal: status columns and captions say Over / Warning / OK in words.
Empty data produces a "No data to display" chart instead of an error.

## 7. Limitations
- Descriptive analysis only; no forecasting. The budget suggestion is a simple average, so it reacts slowly to a change in habits and cannot know about one-off costs.
- Sample data covers three months, so month-to-month trends are illustrative.
- Percentages are rounded to one decimal; totals are exact because money is kept as DECIMAL in MySQL.
