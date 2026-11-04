"""Descriptive analysis with Pandas and NumPy. All functions take plain data and return DataFrames/dicts."""
import numpy as np
import pandas as pd

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

TXN_COLS = ["transaction_id", "transaction_date", "transaction_type",
            "category_id", "category_name", "amount", "description"]


def transactions_df(rows):
    """Build a clean transactions DataFrame from DB rows (list of dicts)."""
    df = pd.DataFrame(rows, columns=TXN_COLS)
    df["amount"] = df["amount"].astype(float)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["year"] = df["transaction_date"].dt.year
    df["month"] = df["transaction_date"].dt.month
    return df


def _safe_pct(numerator, denominator):
    """Elementwise numerator/denominator*100, returning 0 where denominator <= 0."""
    num = np.asarray(numerator, dtype=float) * 100.0
    den = np.asarray(denominator, dtype=float)
    return np.divide(num, den, out=np.zeros_like(num), where=den > 0)


def monthly_summary(df, year):
    """Income, expense, savings and savings rate for each month of `year` (12 rows)."""
    d = df[df["year"] == year]
    pivot = d.pivot_table(index="month", columns="transaction_type",
                          values="amount", aggfunc="sum", fill_value=0.0)
    pivot = pivot.reindex(range(1, 13), fill_value=0.0)
    for col in ("income", "expense"):
        if col not in pivot.columns:
            pivot[col] = 0.0
    out = pd.DataFrame({
        "month": np.arange(1, 13),
        "month_name": MONTH_NAMES,
        "income": pivot["income"].to_numpy(dtype=float),
        "expense": pivot["expense"].to_numpy(dtype=float),
    })
    out["savings"] = np.round(out["income"] - out["expense"], 2)
    out["savings_rate"] = np.round(_safe_pct(out["savings"], out["income"]), 1)
    return out


def period_totals(df, year, month=0):
    """Totals for one month, or the whole year when month is 0."""
    d = df[df["year"] == year]
    if month:
        d = d[d["month"] == month]
    income = float(d.loc[d["transaction_type"] == "income", "amount"].sum())
    expense = float(d.loc[d["transaction_type"] == "expense", "amount"].sum())
    savings = round(income - expense, 2)
    rate = float(_safe_pct([savings], [income])[0])
    return {"income": round(income, 2), "expense": round(expense, 2),
            "savings": savings, "savings_rate": round(rate, 1)}


def category_expense(df, year, month=0):
    """Expense per category (sorted high to low) with share of total."""
    d = df[(df["year"] == year) & (df["transaction_type"] == "expense")]
    if month:
        d = d[d["month"] == month]
    out = (d.groupby(["category_id", "category_name"], as_index=False)["amount"]
             .sum().sort_values("amount", ascending=False).reset_index(drop=True))
    total = out["amount"].sum()
    out["pct"] = np.round(_safe_pct(out["amount"], np.full(len(out), total)), 1)
    out["amount"] = out["amount"].round(2)
    return out


def category_month_pivot(df, year):
    """Expense matrix: rows = category, columns = months 1..12, plus a Total column."""
    d = df[(df["year"] == year) & (df["transaction_type"] == "expense")]
    pivot = d.pivot_table(index="category_name", columns="month",
                          values="amount", aggfunc="sum", fill_value=0.0)
    pivot = pivot.reindex(columns=range(1, 13), fill_value=0.0)
    pivot["Total"] = pivot.sum(axis=1)
    return pivot.sort_values("Total", ascending=False).round(2)


def budget_status(df, budget_rows, year, month):
    """Compare actual spending with the budget for each budgeted category.

    Status: 'Over' if spent > budget, 'Warning' if utilization >= 80%, else 'OK'.
    """
    cols = ["category_id", "category_name", "budget_amount", "spent",
            "remaining", "over_by", "utilization", "status"]
    if not budget_rows:
        return pd.DataFrame(columns=cols)
    budgets = pd.DataFrame(budget_rows)[["category_id", "category_name", "budget_amount"]]
    budgets["budget_amount"] = budgets["budget_amount"].astype(float)

    d = df[(df["year"] == year) & (df["month"] == month) & (df["transaction_type"] == "expense")]
    spent = d.groupby("category_id")["amount"].sum().rename("spent").reset_index()

    out = budgets.merge(spent, on="category_id", how="left")
    out["spent"] = out["spent"].fillna(0.0)
    out["remaining"] = np.round(out["budget_amount"] - out["spent"], 2)
    out["over_by"] = np.round(np.maximum(out["spent"] - out["budget_amount"], 0.0), 2)
    out["utilization"] = np.round(_safe_pct(out["spent"], out["budget_amount"]), 1)
    out["status"] = np.where(out["spent"] > out["budget_amount"], "Over",
                             np.where(out["utilization"] >= 80, "Warning", "OK"))
    return out.sort_values("utilization", ascending=False).reset_index(drop=True)[cols]


def savings_report(summary):
    """Yearly savings insights from a monthly_summary frame using NumPy."""
    active = summary[(summary["income"] > 0) | (summary["expense"] > 0)]
    if active.empty:
        return None
    s = active["savings"].to_numpy()
    names = active["month_name"].to_numpy()
    return {
        "total_savings": round(float(s.sum()), 2),
        "average_monthly_savings": round(float(s.mean()), 2),
        "best_month": f"{names[int(np.argmax(s))]} ({s.max():,.2f})",
        "worst_month": f"{names[int(np.argmin(s))]} ({s.min():,.2f})",
        "deficit_months": int((s < 0).sum()),
        "active_months": int(len(s)),
    }


# ---------- feature: previous-month helper, smart insights, budget suggestions ----------
def previous_month(year, month):
    """(year, month) of the month before the given one."""
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _money(value, currency):
    return f"{currency}{value:,.2f}"


def insights(df, status, year, month, currency="₹"):
    """Plain-language findings for a month (or a whole year when month is 0).

    Returns a list of {"level": "good" | "warning" | "info", "text": str}. Every sentence comes
    from a simple rule on numbers already computed above, so each one can be traced to a formula.
    """
    scope = f"{MONTH_NAMES[month - 1]} {year}" if month else str(year)
    totals = period_totals(df, year, month)
    if totals["income"] == 0 and totals["expense"] == 0:
        return [{"level": "info", "text": f"No transactions are recorded for {scope} yet."}]

    out = []
    # 1. Savings: income minus expenses
    if totals["income"] > 0:
        if totals["savings"] >= 0:
            out.append({"level": "good", "text": f"You saved {_money(totals['savings'], currency)} in {scope}, "
                                                  f"which is {totals['savings_rate']}% of your income."})
        else:
            out.append({"level": "warning", "text": f"You spent {_money(-totals['savings'], currency)} more than "
                                                     f"you earned in {scope}."})
    else:
        out.append({"level": "info", "text": f"No income is recorded for {scope}, so the savings rate is shown as 0%."})

    # 2. Spending compared with the previous month
    if month:
        py, pm = previous_month(year, month)
        prev = period_totals(df, py, pm)
        if prev["expense"] > 0:
            change = (totals["expense"] - prev["expense"]) / prev["expense"] * 100
            if abs(change) < 0.05:
                out.append({"level": "info", "text": f"Spending is unchanged from {MONTH_NAMES[pm - 1]} {py}."})
            else:
                direction = "up" if change > 0 else "down"
                level = "warning" if change > 10 else "info"
                out.append({"level": level, "text": f"Spending is {direction} {abs(change):.1f}% compared with "
                                                    f"{MONTH_NAMES[pm - 1]} {py} ({_money(prev['expense'], currency)} "
                                                    f"to {_money(totals['expense'], currency)})."})

    # 3. Largest expense category
    cats = category_expense(df, year, month)
    if not cats.empty:
        top = cats.iloc[0]
        out.append({"level": "info", "text": f"{top['category_name']} is your largest expense: "
                                              f"{_money(top['amount'], currency)} ({top['pct']}% of spending)."})

    # 4. Budget findings
    if status is not None and not status.empty:
        for _, r in status[status["status"] == "Over"].iterrows():
            out.append({"level": "warning", "text": f"{r['category_name']} is {r['utilization'] - 100:.0f}% over its budget "
                                                    f"(over by {_money(r['over_by'], currency)})."})
        for _, r in status[status["status"] == "Warning"].iterrows():
            out.append({"level": "warning", "text": f"{r['category_name']} has used {r['utilization']:.0f}% of its budget; "
                                                    f"{_money(r['remaining'], currency)} left."})
        if not (status["status"] != "OK").any():
            out.append({"level": "good", "text": "All budgeted categories are within their limits."})
    return out


def budget_suggestions(df, year, month, window=3, round_to=100):
    """Suggest a monthly limit for each expense category.

    Method: take the `window` calendar months before the chosen month, keep the months that have
    any expense (so an empty month does not drag the average down), average each category's
    spending over those months, and round UP to the next `round_to` (default 100).
    Returns one row per category with: average_spend, suggested, months_used.
    """
    cols = ["category_id", "category_name", "average_spend", "suggested", "months_used"]
    exp = df[df["transaction_type"] == "expense"].copy()
    exp["period"] = exp["year"] * 12 + exp["month"] - 1
    target = year * 12 + month - 1
    d = exp[(exp["period"] >= target - window) & (exp["period"] < target)]
    if d.empty:
        return pd.DataFrame(columns=cols)

    monthly = (d.groupby(["category_id", "category_name", "period"])["amount"].sum()
                .unstack("period", fill_value=0.0))          # rows = category, columns = active months
    average = np.round(monthly.mean(axis=1).to_numpy(dtype=float), 2)
    out = monthly.index.to_frame(index=False)
    out["average_spend"] = average
    out["suggested"] = np.ceil(average / round_to) * round_to
    out["months_used"] = int(monthly.shape[1])
    return out.sort_values("suggested", ascending=False).reset_index(drop=True)[cols]


# ---------- feature: advised budget from a salary ----------
DEFAULT_SPLIT = {"rent": 30, "groceries": 15, "utilities": 8, "transportation": 8, "healthcare": 5,
                 "education": 6, "entertainment": 6, "other expense": 4}


def salary_budget_plan(df, salary, expense_categories, year, month, window=6, savings_pct=20,
                       round_to=50, max_categories=8):
    """Advise a budget for each category when a salary is added.

    Categories: the most frequently used expense categories in the earlier months (used in at least
    half of them, at most `max_categories`). Amounts: `savings_pct`% of the salary is kept aside, the
    rest is shared in proportion to what the user normally spends in each category. With no history
    yet, a typical split (rent 30, groceries 15, ...) is used instead.
    Returns {"rows": [...], "spendable": x, "savings": y, "based_on": text}.
    """
    salary = float(salary or 0)
    empty = {"rows": [], "spendable": 0.0, "savings": 0.0, "based_on": ""}
    if salary <= 0 or not expense_categories:
        return empty
    savings = round(salary * savings_pct / 100, 2)
    spendable = round(salary - savings, 2)

    exp = df[df["transaction_type"] == "expense"].copy()
    exp["p"] = exp["year"] * 12 + exp["month"] - 1
    target = year * 12 + month - 1
    hist = exp[(exp["p"] >= target - window) & (exp["p"] < target)]
    observed = int(hist["p"].nunique())
    weights = []  # (category, weight, note)
    if observed:
        monthly = hist.groupby(["category_id", "p"])["amount"].sum().reset_index()
        stats = monthly.groupby("category_id").agg(months=("p", "nunique"), avg=("amount", "mean"))
        names = {c["category_id"]: c["category_name"] for c in expense_categories}
        ranked = sorted(((cid, r["months"], r["avg"]) for cid, r in stats.iterrows() if cid in names),
                        key=lambda t: (-t[1], -t[2]))
        chosen = [t for t in ranked if t[1] / observed >= 0.5] or ranked[:5]
        for cid, months, avg in chosen[:max_categories]:
            weights.append(({"category_id": cid, "category_name": names[cid]}, float(avg),
                            f"Used in {months} of the last {observed} month{'s' if observed != 1 else ''}"))
        based_on = f"your most frequently used categories over the last {observed} month{'s' if observed != 1 else ''}"
    else:
        for c in expense_categories:
            w = DEFAULT_SPLIT.get(c["category_name"].strip().lower())
            if w:
                weights.append((c, float(w), "Typical split (no spending history yet)"))
        based_on = "a typical household split, because there is no spending history yet"
    total = sum(w for _, w, _ in weights)
    if total <= 0:
        return empty
    rows = []
    for c, w, note in weights:
        advised = max(round_to, round(spendable * w / total / round_to) * round_to)
        rows.append({"category_id": c["category_id"], "category_name": c["category_name"],
                     "share": round(w / total * 100, 1), "advised": float(advised), "note": note})
    rows.sort(key=lambda r: -r["advised"])
    return {"rows": rows, "spendable": spendable, "savings": savings, "based_on": based_on}
