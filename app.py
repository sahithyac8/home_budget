import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pymysql
from flask import (Flask, Response, abort, flash, g, jsonify, redirect,
                   render_template, request, session, url_for)

import analysis
import charts
import csv_io
import db
import month_categories
from auth import auth
from config import SECRET_KEY_IS_RANDOM, Config
from validation import validate_transaction

app = Flask(__name__)
app.config.from_object(Config)
app.config["MAX_CONTENT_LENGTH"] = 1_000_000  # reject uploads over 1 MB
app.teardown_appcontext(db.close_db)
app.register_blueprint(auth)  # /register, /login, /logout live in auth.py
if SECRET_KEY_IS_RANDOM:
    app.logger.warning("SECRET_KEY is not set: using a random key, so logins reset on every restart.")

INSERT_TRANSACTION = """INSERT INTO transactions
    (user_id, transaction_date, transaction_type, category_id, amount, description)
    VALUES (%(user_id)s, %(transaction_date)s, %(transaction_type)s, %(category_id)s, %(amount)s, %(description)s)"""

# Pages a visitor can open without logging in. Everything else needs an account.
PUBLIC_ENDPOINTS = {"landing", "auth.login", "auth.register"}


MONTH_CATEGORY_DDL = """CREATE TABLE IF NOT EXISTS month_categories (
    id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, category_id INT NOT NULL,
    cat_year SMALLINT NOT NULL, cat_month TINYINT NOT NULL, status ENUM('added','dismissed') NOT NULL,
    CONSTRAINT fk_mc_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_mc_category FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE CASCADE,
    UNIQUE KEY uq_month_category (user_id, category_id, cat_year, cat_month)) ENGINE=InnoDB"""
_month_table_ready = False


def ensure_month_table():
    """Create the month_categories table on first use, so an already-deployed database upgrades itself."""
    global _month_table_ready
    if _month_table_ready or app.config.get("TESTING"):
        return
    db.execute(MONTH_CATEGORY_DDL)
    _month_table_ready = True


# ---------- helpers ----------
@app.template_filter("money")
def money(value):
    return f"{app.config['CURRENCY']}{float(value or 0):,.2f}"


@app.context_processor
def inject_globals():
    return {"month_names": analysis.MONTH_NAMES, "today": date.today(), "user": g.get("user")}


def uid():
    """The id of the logged-in user. Every query on money data filters by it."""
    return g.user["user_id"]


@app.before_request
def load_user_and_require_login():
    """Find the logged-in user; send everyone else to the login page (pages are private by default)."""
    g.user = None
    if request.endpoint in ("static", "health"):
        return None
    if "user_id" in session:
        g.user = db.query_one("SELECT user_id, full_name FROM users WHERE user_id = %s", (session["user_id"],))
        if g.user is None:
            session.clear()  # the account no longer exists
        else:
            ensure_month_table()
    if request.endpoint is not None and g.user is None and request.endpoint not in PUBLIC_ENDPOINTS:
        if request.path.startswith("/api/"):
            return jsonify(error="Please log in first."), 401
        target = request.full_path.rstrip("?") if request.method == "GET" else None
        return redirect(url_for("auth.login", next=target))
    return None


@app.after_request
def add_safety_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if request.endpoint != "static":
        response.headers.setdefault("Cache-Control", "no-store")  # logged-in pages are never cached
    return response


def period_args(default_month=None):
    """Read ?year=&month= with safe defaults. month 0 means the whole year."""
    t = date.today()
    year = request.args.get("year", type=int) or t.year
    year = min(max(year, 2000), 2100)
    month = request.args.get("month", type=int)
    if month is None:
        month = t.month if default_month is None else default_month
    month = min(max(month, 0), 12)
    return year, month


def fetch_transactions():
    return db.query_all(
        """SELECT t.transaction_id, t.transaction_date, t.transaction_type,
                  t.category_id, c.category_name, t.amount, t.description
           FROM transactions t JOIN categories c ON c.category_id = t.category_id
           WHERE t.user_id = %s
           ORDER BY t.transaction_date DESC, t.transaction_id DESC""", (uid(),))


def fetch_budgets(year, month):
    return db.query_all(
        """SELECT b.category_id, c.category_name, b.budget_amount
           FROM monthly_budgets b JOIN categories c ON c.category_id = b.category_id
           WHERE b.user_id = %s AND b.budget_year = %s AND b.budget_month = %s""", (uid(), year, month))


def parse_transaction(form):
    """Validate the transaction form (rules live in validation.py). Returns (data, errors)."""
    cat_id = form.get("category_id", type=int)
    category = (db.query_one("SELECT * FROM categories WHERE category_id = %s AND user_id = %s",
                              (cat_id, uid()))
                if cat_id else None)
    data, errors = validate_transaction(form.get("transaction_date"), form.get("transaction_type"),
                                        form.get("amount"), category, form.get("description"))
    data["category_id"] = cat_id  # keep the user's choice when the form is shown again
    return data, errors


def month_context(year, month):
    """Everything the dashboard-style pages need for one month."""
    df = analysis.transactions_df(fetch_transactions())
    status = analysis.budget_status(df, fetch_budgets(year, month), year, month) if month else None
    return df, status


# ---------- health check and error pages ----------
@app.route("/health")
def health():
    """Used to confirm the app can reach MySQL (also handy before the demonstration)."""
    try:
        db.query_one("SELECT 1 AS ok")
        return jsonify(status="ok", database="up")
    except (pymysql.err.MySQLError, OSError):
        return jsonify(status="error", database="down"), 503


def error_page(code, title, message):
    return render_template("error.html", code=code, title=title, message=message), code


@app.errorhandler(404)
def not_found(_):
    return error_page(404, "Page not found", "The page or record you asked for does not exist.")


@app.errorhandler(413)
def too_large(_):
    return error_page(413, "File too large", "Uploads are limited to 1 MB.")


@app.errorhandler(pymysql.err.MySQLError)
def database_error(exc):
    app.logger.error("Database error: %s", exc)
    return error_page(503, "Database unavailable",
                      "The application could not use the MySQL database. Check that MySQL is "
                      "running and that the MYSQL_* environment variables are correct.")


@app.errorhandler(500)
def server_error(_):
    return error_page(500, "Something went wrong", "An unexpected error occurred. Please try again.")


# ---------- landing page and dashboard ----------
@app.route("/")
def landing():
    if g.user:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")


@app.route("/dashboard")
def dashboard():
    year, month = period_args()
    month = month or date.today().month  # the dashboard always shows one month
    df, status = month_context(year, month)
    totals = analysis.period_totals(df, year, month)
    cats = analysis.category_expense(df, year, month)
    violations = status[status["status"] == "Over"].to_dict("records")
    return render_template("dashboard.html", year=year, month=month, totals=totals,
                           cats=cats.to_dict("records"), status=status.to_dict("records"),
                           violations=violations,
                           insights=analysis.insights(df, status, year, month, app.config["CURRENCY"]))


# ---------- transactions CRUD ----------
@app.route("/transactions")
def transactions():
    ttype = request.args.get("type", "")
    cat = request.args.get("category", type=int)
    ym = request.args.get("month", "")
    sql = """SELECT t.*, c.category_name FROM transactions t
             JOIN categories c ON c.category_id = t.category_id WHERE t.user_id = %s"""
    args = [uid()]
    if ttype in ("income", "expense"):
        sql += " AND t.transaction_type = %s"
        args.append(ttype)
    if cat:
        sql += " AND t.category_id = %s"
        args.append(cat)
    if ym:
        try:
            start = datetime.strptime(ym, "%Y-%m").date()
            sql += " AND t.transaction_date >= %s AND t.transaction_date < %s"
            end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
            args += [start, end]
        except ValueError:
            flash("Ignored invalid month filter.", "error")
    sql += " ORDER BY t.transaction_date DESC, t.transaction_id DESC LIMIT 500"
    rows = db.query_all(sql, args)
    categories = db.query_all("SELECT * FROM categories WHERE user_id = %s ORDER BY category_type, category_name",
                              (uid(),))
    return render_template("transactions.html", rows=rows, categories=categories,
                           f_type=ttype, f_cat=cat, f_month=ym)


def _form_page(txn, errors=None):
    categories = db.query_all("SELECT * FROM categories WHERE user_id = %s ORDER BY category_name", (uid(),))
    when = txn.get("transaction_date")
    if isinstance(when, str):
        try:
            when = datetime.strptime(when, "%Y-%m-%d").date()
        except ValueError:
            when = None
    when = when or date.today()
    plan = plan_for_month(when.year, when.month)  # that month's own categories are listed first
    month_ids = {i["category_id"] for i in plan["active"]}
    return render_template("transaction_form.html", txn=txn, categories=categories, month_ids=month_ids,
                           errors=errors or [])


@app.route("/transactions/add", methods=["GET", "POST"])
def add_transaction():
    if request.method == "POST":
        data, errors = parse_transaction(request.form)
        if errors:
            return _form_page(data, errors), 400
        data["user_id"] = uid()
        db.execute(INSERT_TRANSACTION, data)
        flash("Transaction added.", "success")
        category = db.query_one("SELECT * FROM categories WHERE category_id = %s AND user_id = %s",
                                (data["category_id"], uid()))
        if data["transaction_type"] == "income" and category and category["category_name"].strip().lower() == "salary":
            when = data["transaction_date"]  # a salary: go straight to the advised budget for that month
            return redirect(url_for("budgets", year=when.year, month=when.month, salary=f"{data['amount']:.2f}"))
        return redirect(url_for("transactions"))
    return _form_page({"transaction_date": date.today(), "transaction_type": "expense"})


@app.route("/transactions/<int:txn_id>/edit", methods=["GET", "POST"])
def edit_transaction(txn_id):
    existing = db.query_one("SELECT * FROM transactions WHERE transaction_id = %s AND user_id = %s",
                            (txn_id, uid()))
    if not existing:
        abort(404)
    if request.method == "POST":
        data, errors = parse_transaction(request.form)
        data["transaction_id"] = txn_id
        if errors:
            return _form_page(data, errors), 400
        data["user_id"] = uid()
        db.execute("""UPDATE transactions SET transaction_date=%(transaction_date)s,
                      transaction_type=%(transaction_type)s, category_id=%(category_id)s,
                      amount=%(amount)s, description=%(description)s
                      WHERE transaction_id=%(transaction_id)s AND user_id=%(user_id)s""", data)
        flash("Transaction updated.", "success")
        return redirect(url_for("transactions"))
    return _form_page(existing)


@app.route("/transactions/<int:txn_id>/delete", methods=["POST"])
def delete_transaction(txn_id):
    db.execute("DELETE FROM transactions WHERE transaction_id = %s AND user_id = %s", (txn_id, uid()))
    flash("Transaction deleted.", "success")
    return redirect(request.referrer or url_for("transactions"))


# ---------- categories (month-wise) ----------
def month_args():
    """?year=&month= for the category pages; a category list is always for one real month."""
    year, month = period_args(default_month=date.today().month)
    return year, (month or date.today().month)


def expense_categories():
    return db.query_all("SELECT * FROM categories WHERE user_id = %s AND category_type='expense' ORDER BY category_name",
                        (uid(),))


def month_overrides(year, month):
    rows = db.query_all("SELECT category_id, status FROM month_categories WHERE user_id = %s "
                        "AND cat_year = %s AND cat_month = %s", (uid(), year, month))
    return {r["category_id"]: r["status"] for r in rows}


def plan_for_month(year, month, df=None):
    if df is None:
        df = analysis.transactions_df(fetch_transactions())
    return month_categories.category_plan(df, expense_categories(), month_overrides(year, month), year, month)


def set_month_status(cat_id, year, month, status):
    db.execute("""INSERT INTO month_categories (user_id, category_id, cat_year, cat_month, status)
                  VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE status = VALUES(status)""",
               (uid(), cat_id, year, month, status))


@app.route("/categories", methods=["GET", "POST"])
def categories():
    if request.method == "POST":
        year = request.form.get("year", type=int) or date.today().year
        month = request.form.get("month", type=int) or date.today().month
        name = request.form.get("category_name", "").strip()
        ctype = request.form.get("category_type")
        if not name or len(name) > 50 or ctype not in ("income", "expense"):
            flash("Enter a category name (max 50 characters) and a type.", "error")
        else:
            try:
                db.execute("INSERT INTO categories (user_id, category_name, category_type) VALUES (%s, %s, %s)",
                           (uid(), name, ctype))
                if ctype == "expense":  # a new expense category is added to the month being viewed
                    db.execute("""INSERT INTO month_categories (user_id, category_id, cat_year, cat_month, status)
                                  SELECT user_id, category_id, %s, %s, 'added' FROM categories
                                  WHERE user_id = %s AND category_name = %s AND category_type = 'expense'
                                  ON DUPLICATE KEY UPDATE status = 'added'""", (year, month, uid(), name))
                flash("Category added.", "success")
            except pymysql.err.IntegrityError:
                flash("That category already exists.", "error")
        return redirect(url_for("categories", year=year, month=month))
    year, month = month_args()
    plan = plan_for_month(year, month)
    rows = db.query_all("""SELECT c.*, COUNT(t.transaction_id) AS txn_count
                           FROM categories c LEFT JOIN transactions t ON t.category_id = c.category_id
                           WHERE c.user_id = %s
                           GROUP BY c.category_id ORDER BY c.category_type, c.category_name""", (uid(),))
    return render_template("categories.html", rows=rows, plan=plan, year=year, month=month)


@app.route("/categories/<int:cat_id>/month", methods=["POST"])
def change_month_category(cat_id):
    """Delete a suggested category from one month ('remove') or put one back / add one ('add')."""
    year = request.form.get("year", type=int) or date.today().year
    month = request.form.get("month", type=int) or date.today().month
    action = request.form.get("action")
    category = db.query_one("SELECT * FROM categories WHERE category_id = %s AND user_id = %s", (cat_id, uid()))
    if not category or action not in ("add", "remove") or not 1 <= month <= 12:
        abort(404)
    if action == "remove":
        df = analysis.transactions_df(fetch_transactions())
        used = ((df["category_id"] == cat_id) & (df["year"] == year) & (df["month"] == month)).any()
        if used:
            flash(f"{category['category_name']} has transactions in {analysis.MONTH_NAMES[month - 1]} {year}, "
                  "so it stays in that month.", "error")
        else:
            set_month_status(cat_id, year, month, "dismissed")
            flash(f"{category['category_name']} removed from {analysis.MONTH_NAMES[month - 1]} {year}.", "success")
    else:
        set_month_status(cat_id, year, month, "added")
        flash(f"{category['category_name']} added to {analysis.MONTH_NAMES[month - 1]} {year}.", "success")
    return redirect(url_for("categories", year=year, month=month))


@app.route("/categories/<int:cat_id>/delete", methods=["POST"])
def delete_category(cat_id):
    try:
        db.execute("DELETE FROM categories WHERE category_id = %s AND user_id = %s", (cat_id, uid()))
        flash("Category deleted.", "success")
    except pymysql.err.IntegrityError:
        flash("Cannot delete a category that has transactions.", "error")
    return redirect(url_for("categories"))


# ---------- budgets (with feature 3: budget suggestions) ----------
@app.route("/budgets", methods=["GET", "POST"])
def budgets():
    year, month = period_args(default_month=date.today().month)
    month = month or date.today().month  # budgets are always per month
    if request.method == "POST":
        year = request.form.get("year", type=int) or year
        month = request.form.get("month", type=int) or month
        expense_cats = db.query_all("SELECT category_id FROM categories WHERE user_id = %s AND category_type='expense'",
                                    (uid(),))
        errors = 0
        for c in expense_cats:
            raw = request.form.get(f"budget_{c['category_id']}", "").strip()
            if raw == "":
                db.execute("""DELETE FROM monthly_budgets WHERE user_id=%s AND category_id=%s
                              AND budget_month=%s AND budget_year=%s""",
                           (uid(), c["category_id"], month, year))
                continue
            try:
                amt = Decimal(raw)
                if not amt.is_finite() or amt < 0 or amt >= Decimal("10000000000"):
                    raise InvalidOperation
            except InvalidOperation:
                errors += 1
                continue
            if amt == 0:
                db.execute("""DELETE FROM monthly_budgets WHERE user_id=%s AND category_id=%s
                              AND budget_month=%s AND budget_year=%s""",
                           (uid(), c["category_id"], month, year))
            else:
                db.execute("""INSERT INTO monthly_budgets (user_id, category_id, budget_month, budget_year, budget_amount)
                              VALUES (%s, %s, %s, %s, %s)
                              ON DUPLICATE KEY UPDATE budget_amount = VALUES(budget_amount)""",
                           (uid(), c["category_id"], month, year, round(amt, 2)))
        flash("Budgets saved." if not errors else f"Saved, but {errors} invalid value(s) were skipped.",
              "success" if not errors else "error")
        return redirect(url_for("budgets", year=year, month=month))

    cats = db.query_all("SELECT * FROM categories WHERE user_id = %s AND category_type='expense' ORDER BY category_name",
                        (uid(),))
    current = {b["category_id"]: f"{b['budget_amount']:.2f}" for b in fetch_budgets(year, month)}
    df = analysis.transactions_df(fetch_transactions())
    status = analysis.budget_status(df, fetch_budgets(year, month), year, month)

    suggestions = analysis.budget_suggestions(df, year, month)
    salary = request.args.get("salary", type=float)
    if salary is not None and not (0 < salary < 10_000_000_000):
        salary = None
    plan = analysis.salary_budget_plan(df, salary, cats, year, month) if salary else None
    prefilled = bool(request.args.get("suggest")) and not suggestions.empty
    form_values = dict(current)
    if plan and plan["rows"]:
        form_values.update({r["category_id"]: f"{r['advised']:.2f}" for r in plan["rows"]})
    elif prefilled:  # shown in the form only; nothing is saved until the user presses Save
        form_values.update({int(r["category_id"]): f"{r['suggested']:.2f}"
                            for r in suggestions.to_dict("records")})
    return render_template("budgets.html", year=year, month=month, cats=cats, current=current,
                           form_values=form_values, prefilled=prefilled, plan=plan, salary=salary,
                           status=status.to_dict("records"),
                           suggestions=suggestions.to_dict("records"))


# ---------- reports ----------
@app.route("/reports")
def reports():
    year, month = period_args(default_month=0)
    df, status = month_context(year, month)
    summary = analysis.monthly_summary(df, year)
    pivot = analysis.category_month_pivot(df, year)
    cats = analysis.category_expense(df, year, month)
    return render_template(
        "reports.html", year=year, month=month,
        summary=summary.to_dict("records"),
        totals=analysis.period_totals(df, year, 0),
        savings=analysis.savings_report(summary),
        pivot_cols=list(pivot.columns), pivot_rows=[(n, list(r)) for n, r in pivot.iterrows()],
        cats=cats.to_dict("records"),
        violations=(status[status["status"] == "Over"].to_dict("records")
                    if status is not None else []),
        insights=analysis.insights(df, status, year, month, app.config["CURRENCY"]))


@app.route("/chart/<name>.png")
def chart(name):
    year, month = period_args()
    df = analysis.transactions_df(fetch_transactions())
    cur = app.config["CURRENCY"]
    scope = f"{analysis.MONTH_NAMES[month - 1]} {year}" if month else str(year)
    if name == "distribution":
        png = charts.expense_distribution(analysis.category_expense(df, year, month),
                                          f"Expense Distribution - {scope}")
    elif name == "monthly":
        png = charts.monthly_comparison(analysis.monthly_summary(df, year), year, cur)
    elif name == "budget":
        if not month:
            abort(400)
        status = analysis.budget_status(df, fetch_budgets(year, month), year, month)
        png = charts.budget_utilization(status, f"Budget Utilization - {scope}")
    elif name == "category_month":
        png = charts.category_by_month(analysis.category_month_pivot(df, year), year, cur)
    else:
        abort(404)
    resp = Response(png, mimetype="image/png")
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ---------- feature 2: CSV export and import ----------
def csv_response(text, filename):
    return Response(text, mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


def months_start(n, today=None):
    """First day of the month that is n-1 months before this one (so n=1 means this month only)."""
    today = today or date.today()
    index = today.year * 12 + today.month - 1 - (n - 1)
    return date(index // 12, index % 12 + 1, 1)


@app.route("/export/transactions.csv")
def export_transactions():
    """Download filtered by ?range=1 | 3 | custom&months=N | all, or by ?year=&month= (older links)."""
    rows = fetch_transactions()
    name = "transactions.csv"
    rng = request.args.get("range", "")
    if rng in ("1", "3", "custom"):
        n = 1 if rng == "1" else 3 if rng == "3" else request.args.get("months", type=int)
        if not n or not 1 <= n <= 240:
            flash("Enter a number of months between 1 and 240.", "error")
            return redirect(url_for("import_transactions"))
        start = months_start(n)
        rows = [r for r in rows if r["transaction_date"] >= start]
        name = f"transactions-last-{n}-month{'s' if n != 1 else ''}.csv"
    else:
        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)
        if year:
            rows = [r for r in rows if r["transaction_date"].year == year]
        if month:
            rows = [r for r in rows if r["transaction_date"].month == month]
    return csv_response(csv_io.transactions_to_csv(rows), name)


@app.route("/export/monthly-summary.csv")
def export_monthly_summary():
    year, _ = period_args(default_month=0)
    df = analysis.transactions_df(fetch_transactions())
    return csv_response(csv_io.summary_to_csv(analysis.monthly_summary(df, year)),
                        f"monthly-summary-{year}.csv")


@app.route("/import", methods=["GET", "POST"])
def import_transactions():
    result = None
    if request.method == "POST":
        upload = request.files.get("file")
        if not upload or not upload.filename:
            flash("Choose a CSV file first.", "error")
        else:
            try:
                text = upload.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                text = None
                flash("The file must be a UTF-8 text (CSV) file.", "error")
            if text is not None:
                categories_ = db.query_all("SELECT * FROM categories WHERE user_id = %s", (uid(),))
                valid, rejected, fatal = csv_io.parse_import(text, categories_)
                if fatal:
                    flash(fatal, "error")
                else:
                    if valid:
                        for row in valid:
                            row["user_id"] = uid()
                        db.execute_many(INSERT_TRANSACTION, valid)
                    result = {"imported": len(valid), "rejected": rejected}
                    flash(f"Imported {len(valid)} row(s); rejected {len(rejected)}.",
                          "success" if not rejected else "error")
    return render_template("import.html", result=result, columns=csv_io.IMPORT_COLUMNS)


# ---------- read-only JSON API ----------
@app.route("/api/transactions")
def api_transactions():
    return jsonify([{"transaction_id": r["transaction_id"],
                     "transaction_date": str(r["transaction_date"]),
                     "transaction_type": r["transaction_type"],
                     "category": r["category_name"],
                     "amount": float(r["amount"]),
                     "description": r["description"]} for r in fetch_transactions()])


@app.route("/api/summary")
def api_summary():
    year, month = period_args(default_month=0)
    df = analysis.transactions_df(fetch_transactions())
    return jsonify(year=year, month=month, totals=analysis.period_totals(df, year, month),
                   monthly=analysis.monthly_summary(df, year).to_dict("records"))


@app.route("/api/budget-status")
def api_budget_status():
    year, month = period_args()
    month = month or date.today().month
    _, status = month_context(year, month)
    return jsonify(year=year, month=month, categories=status.to_dict("records"))


@app.route("/api/insights")
def api_insights():
    year, month = period_args()
    month = month or date.today().month
    df, status = month_context(year, month)
    return jsonify(year=year, month=month,
                   insights=analysis.insights(df, status, year, month, app.config["CURRENCY"]))


if __name__ == "__main__":
    # Debug mode is off unless FLASK_DEBUG=1 is set (never leave it on in a demonstration).
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
