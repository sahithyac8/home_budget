"""Matplotlib charts. Each function returns PNG bytes."""
import io

import matplotlib
matplotlib.use("Agg")  # headless backend for servers
import matplotlib.pyplot as plt
import numpy as np


def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _empty(title):
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.text(0.5, 0.5, "No data to display", ha="center", va="center", color="gray")
    ax.set_title(title)
    ax.set_axis_off()
    return _png(fig)


def expense_distribution(cat_df, title):
    """Pie chart of expenses by category."""
    if cat_df.empty or cat_df["amount"].sum() <= 0:
        return _empty(title)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    wedges, _ = ax.pie(cat_df["amount"], startangle=90, counterclock=False,
                       wedgeprops={"edgecolor": "white"})
    labels = [f"{n} - {p:.1f}%" for n, p in zip(cat_df["category_name"], cat_df["pct"])]
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1, 0.5), frameon=False)
    ax.set_title(title)
    ax.axis("equal")
    return _png(fig)


def monthly_comparison(summary, year, currency="₹"):
    """Income vs expense bars per month with a savings line."""
    if summary[["income", "expense"]].to_numpy().sum() <= 0:
        return _empty(f"Income vs Expenses - {year}")
    x = np.arange(12)
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(x - w / 2, summary["income"], w, label="Income", color="#2e7d32")
    ax.bar(x + w / 2, summary["expense"], w, label="Expenses", color="#c62828")
    ax.plot(x, summary["savings"], color="#1565c0", marker="o", label="Savings")
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(summary["month_name"])
    ax.set_xlabel("Month")
    ax.set_ylabel(f"Amount ({currency})")
    ax.set_title(f"Monthly Income vs Expenses - {year}")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3)
    return _png(fig)


def budget_utilization(status_df, title):
    """Horizontal bars showing % of budget used; red when over budget."""
    if status_df.empty:
        return _empty(title)
    df = status_df.iloc[::-1]
    colors = ["#c62828" if s == "Over" else "#ef6c00" if s == "Warning" else "#2e7d32"
              for s in df["status"]]
    fig, ax = plt.subplots(figsize=(7, max(2.5, 0.55 * len(df) + 1)))
    bars = ax.barh(df["category_name"], df["utilization"], color=colors)
    ax.axvline(100, color="black", linestyle="--", linewidth=1)
    for bar, val in zip(bars, df["utilization"]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{val:.0f}%", va="center", fontsize=9)
    ax.set_xlim(0, max(120, float(df["utilization"].max()) + 15))
    ax.set_xlabel("Budget used (%)")
    ax.set_ylabel("Expense category")
    ax.set_title(title)
    return _png(fig)


def category_by_month(pivot, year, currency="₹"):
    """Stacked monthly expense bars split by category."""
    title = f"Expenses by Category and Month - {year}"
    if pivot.empty:
        return _empty(title)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    data = pivot.drop(columns="Total")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bottom = np.zeros(12)
    for name, row in data.iterrows():
        vals = row.to_numpy(dtype=float)
        ax.bar(months, vals, bottom=bottom, label=name)
        bottom += vals
    ax.set_xlabel("Month")
    ax.set_ylabel(f"Expenses ({currency})")
    ax.set_title(title)
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), frameon=False)
    ax.grid(axis="y", alpha=0.3)
    return _png(fig)
