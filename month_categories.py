"""Month-wise categories.

Every month has its own category list. It is suggested from the previous months:

  Core        used in at least 60% of the recent months that have expenses (rent, groceries, bills...)
  Occasional  used in 25% to 59% of them (school fees, insurance... things that come up now and then)
  (nothing)   used less than that, so it is not suggested (it can still be added by hand)

The user can delete a suggestion for a month ('dismissed') or add a category by hand ('added').
A category that already has a transaction in that month always stays in the list.
"""
import pandas as pd

WINDOW = 6                 # how many earlier months are looked at
CORE_AT, OCCASIONAL_AT = 0.60, 0.25
# Used only when there is no history yet (a brand-new account).
STARTER_CORE = {"rent", "groceries", "utilities", "transportation"}
STARTER_OCCASIONAL = {"healthcare", "education", "entertainment", "other expense"}
RANK = {"Core": 0, "Occasional": 1}


def category_plan(df, expense_categories, overrides, year, month, window=WINDOW):
    """Return {"active": [...], "removed": [...], "other": [...], "observed": n}.

    expense_categories: list of category dicts; overrides: {category_id: 'added' | 'dismissed'}.
    """
    target = year * 12 + month - 1
    exp = df[df["transaction_type"] == "expense"].copy()
    exp["p"] = exp["year"] * 12 + exp["month"] - 1
    hist = exp[(exp["p"] >= target - window) & (exp["p"] < target)]
    observed = int(hist["p"].nunique())
    used_months = hist.groupby("category_id")["p"].nunique() if observed else pd.Series(dtype=int)
    now = exp[exp["p"] == target].groupby("category_id").size()

    active, removed, other = [], [], []
    for c in expense_categories:
        cid, name = c["category_id"], c["category_name"]
        months_used = int(used_months.get(cid, 0))
        n_now = int(now.get(cid, 0))
        if observed:
            freq = months_used / observed
            priority = "Core" if freq >= CORE_AT else "Occasional" if freq >= OCCASIONAL_AT else None
            reason = f"Used in {months_used} of the last {observed} month{'s' if observed != 1 else ''}"
        else:
            freq = None
            low = name.strip().lower()
            priority = "Core" if low in STARTER_CORE else "Occasional" if low in STARTER_OCCASIONAL else None
            reason = "Starter suggestion (no earlier months yet)"
        item = {"category_id": cid, "category_name": name, "priority": priority, "reason": reason,
                "txn_count": n_now, "can_remove": n_now == 0, "suggested": False,
                "freq_pct": None if freq is None else round(freq * 100)}
        override = overrides.get(cid)
        if n_now == 0 and override == "dismissed":
            removed.append(item)
        elif n_now > 0:
            item["priority"] = item["priority"] or "Used"
            item["reason"] = f"{n_now} transaction{'s' if n_now != 1 else ''} this month. " + reason
            active.append(item)
        elif override == "added":
            item["priority"] = item["priority"] or "Added"
            active.append(item)
        elif priority:
            item["suggested"] = True
            active.append(item)
        else:
            other.append(item)

    active.sort(key=lambda i: (RANK.get(i["priority"], 2), -(i["freq_pct"] or 0), i["category_name"]))
    return {"active": active, "removed": removed, "other": other, "observed": observed}
