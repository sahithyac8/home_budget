"""Input validation shared by the web forms and the CSV import.

Nothing here touches the database, so every rule can be unit-tested on its own.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation

MAX_AMOUNT = Decimal("9999999999.99")  # the largest value DECIMAL(12,2) can hold
MIN_YEAR, MAX_YEAR = 2000, 2100


def parse_date(text):
    """Return a date for 'YYYY-MM-DD', or None when the text is not a real date."""
    try:
        return datetime.strptime((text or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_amount(text):
    """Return (Decimal, None) for a valid amount, else (None, error message).

    Valid = a number from 0.01 to 9,999,999,999.99 with at most 2 decimal places.
    Decimal is used instead of float so that money is never rounded by accident.
    """
    try:
        amount = Decimal((text or "").strip())
    except InvalidOperation:
        return None, "Enter an amount greater than 0."
    if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT:
        return None, "Enter an amount greater than 0 and up to 9,999,999,999.99."
    if amount.as_tuple().exponent < -2:
        return None, "Amount can have at most 2 decimal places."
    return amount, None


def validate_transaction(date_text, ttype, amount_text, category, description=""):
    """Validate one transaction.

    `category` is the matching row of the categories table (a dict) or None.
    Returns (data, errors). `data` can be saved when `errors` is empty; when it is not,
    the raw text is kept in `data` so the form can show what the user typed.
    """
    errors = []

    txn_date = parse_date(date_text)
    if txn_date is None:
        errors.append("Enter a valid date (YYYY-MM-DD).")
    elif not MIN_YEAR <= txn_date.year <= MAX_YEAR:
        errors.append(f"Date must be between the years {MIN_YEAR} and {MAX_YEAR}.")

    if ttype not in ("income", "expense"):
        errors.append("Choose income or expense.")

    amount, amount_error = parse_amount(amount_text)
    if amount_error:
        errors.append(amount_error)

    if category is None:
        errors.append("Choose a valid category.")
    elif ttype in ("income", "expense") and category["category_type"] != ttype:
        errors.append(f"Category '{category['category_name']}' is not an {ttype} category.")

    data = {
        "transaction_date": txn_date or (date_text or ""),
        "transaction_type": ttype,
        "category_id": category["category_id"] if category else None,
        "amount": amount if amount is not None else (amount_text or ""),
        "description": (description or "").strip()[:255],
    }
    return data, errors
