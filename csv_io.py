"""CSV export and import (Python standard library only).

Export:  transactions and the monthly summary can be downloaded for Excel or reports.
Import:  every row goes through the same validation as the web form; good rows are saved,
         bad rows are listed with the reason so the user can fix and re-upload them.
"""
import csv
import io

from validation import validate_transaction

# The export uses the same columns, so an exported file can be imported again.
IMPORT_COLUMNS = ["transaction_date", "transaction_type", "category", "amount", "description"]
REQUIRED_COLUMNS = IMPORT_COLUMNS[:4]
MAX_IMPORT_ROWS = 1000


def safe_cell(value):
    """Protect against spreadsheet formula injection.

    Excel treats a cell starting with = + - @ as a formula, so such text gets a leading apostrophe.
    """
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def transactions_to_csv(rows):
    """rows = list of dicts with the keys used by app.fetch_transactions()."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(IMPORT_COLUMNS)
    for r in rows:
        writer.writerow([
            str(r["transaction_date"]),
            r["transaction_type"],
            safe_cell(r["category_name"]),
            f"{r['amount']:.2f}",
            safe_cell(r["description"]),
        ])
    return buf.getvalue()


def summary_to_csv(summary):
    """summary = the DataFrame returned by analysis.monthly_summary()."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["month", "income", "expense", "savings", "savings_rate_percent"])
    for r in summary.to_dict("records"):
        writer.writerow([r["month_name"], f"{r['income']:.2f}", f"{r['expense']:.2f}",
                         f"{r['savings']:.2f}", r["savings_rate"]])
    return buf.getvalue()


def parse_import(text, categories):
    """Validate CSV text row by row.

    Returns (valid, rejected, fatal_error):
      valid    - list of clean transaction dicts ready to insert
      rejected - list of {"row": line number, "values": the raw row, "errors": [messages]}
      fatal    - a message when the whole file cannot be used (then the other two are empty)
    """
    by_name = {}  # category name (lower case) -> {"income": row, "expense": row}
    for c in categories:
        by_name.setdefault(c["category_name"].strip().lower(), {})[c["category_type"]] = c

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], [], "The file is empty."
    reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
    missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing:
        return [], [], "Missing column(s): " + ", ".join(missing) + ". Expected: " + ", ".join(IMPORT_COLUMNS) + "."

    valid, rejected = [], []
    for line_no, row in enumerate(reader, start=2):  # line 1 is the header
        if line_no - 1 > MAX_IMPORT_ROWS:
            return [], [], f"Too many rows. Import at most {MAX_IMPORT_ROWS} rows at a time."
        values = {k: (row.get(k) or "").strip() for k in IMPORT_COLUMNS}
        if not any(values.values()):
            continue  # skip a completely blank line
        ttype = values["transaction_type"].lower()
        options = by_name.get(values["category"].lower(), {})
        # Prefer the category of the right type; otherwise pass any match so the error says "not an income category".
        category = options.get(ttype) or next(iter(options.values()), None)
        data, errors = validate_transaction(values["transaction_date"], ttype,
                                            values["amount"], category, values["description"])
        if errors:
            rejected.append({"row": line_no, "values": values, "errors": errors})
        else:
            valid.append(data)
    return valid, rejected, None
