"""Accounts: register, log in, log out.

Passwords are never stored. We store a salted hash (Werkzeug's generate_password_hash) and compare
with check_password_hash when the user logs in. Everything else in the app is protected by the
login check in app.py (before_request), so a new page is private by default.
"""
import time

import pymysql
from flask import (Blueprint, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db
from validation import validate_registration

auth = Blueprint("auth", __name__)

HASH_METHOD = "pbkdf2:sha256:600000"   # slow on purpose, so guessing passwords is expensive
DUMMY_HASH = generate_password_hash("not-a-real-password", method=HASH_METHOD)

# Every new user receives their own copy of these categories.
DEFAULT_CATEGORIES = [
    ("Salary", "income"), ("Business", "income"), ("Interest", "income"), ("Other Income", "income"),
    ("Groceries", "expense"), ("Rent", "expense"), ("Transportation", "expense"),
    ("Healthcare", "expense"), ("Education", "expense"), ("Entertainment", "expense"),
    ("Utilities", "expense"), ("Other Expense", "expense"),
]

# Simple brake on password guessing: 5 wrong passwords for one email -> locked for 10 minutes.
MAX_FAILURES, LOCK_SECONDS = 5, 600
_failures = {}  # email -> (number of failures, time of the first one)


def safe_next_url(target):
    """Only allow redirects to a page on this site (stops 'open redirect' links such as //evil.com)."""
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return None
    return target


def _is_locked(email):
    count, first = _failures.get(email, (0, 0))
    if count >= MAX_FAILURES and time.time() - first < LOCK_SECONDS:
        return True
    if count and time.time() - first >= LOCK_SECONDS:
        _failures.pop(email, None)
    return False


def _record_failure(email):
    if len(_failures) > 5000:   # never let this dictionary grow without limit
        _failures.clear()
    count, first = _failures.get(email, (0, time.time()))
    _failures[email] = (count + 1, first)


def _log_in(user_id):
    session.clear()             # start a fresh session so an old one cannot be reused
    session["user_id"] = user_id


def create_user(full_name, email, password):
    """Insert the user and their default categories together; returns the new user_id."""
    def work(cur):
        cur.execute("INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
                    (full_name, email, generate_password_hash(password, method=HASH_METHOD)))
        user_id = cur.lastrowid
        cur.executemany("INSERT INTO categories (user_id, category_name, category_type) VALUES (%s, %s, %s)",
                        [(user_id, name, ctype) for name, ctype in DEFAULT_CATEGORIES])
        return user_id
    return db.run_in_transaction(work)


@auth.route("/register", methods=["GET", "POST"])
def register():
    if g.get("user"):
        return redirect(url_for("dashboard"))
    values, errors = {"full_name": "", "email": ""}, []
    if request.method == "POST":
        values, errors = validate_registration(request.form.get("full_name"), request.form.get("email"),
                                               request.form.get("password"), request.form.get("confirm"))
        if not errors and db.query_one("SELECT user_id FROM users WHERE email = %s", (values["email"],)):
            errors.append("That email is already registered. Try logging in instead.")
        if not errors:
            try:
                user_id = create_user(values["full_name"], values["email"], request.form["password"])
            except pymysql.err.IntegrityError:   # two sign-ups with the same email at the same moment
                errors.append("That email is already registered. Try logging in instead.")
            else:
                _log_in(user_id)
                flash(f"Welcome, {values['full_name']}! Your account is ready.", "success")
                return redirect(url_for("dashboard"))
    return render_template("register.html", values=values, errors=errors), (400 if errors else 200)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if g.get("user"):
        return redirect(url_for("dashboard"))
    next_url = safe_next_url(request.values.get("next"))
    email, error = "", None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        if _is_locked(email):
            error = "Too many wrong attempts. Please wait 10 minutes and try again."
        else:
            user = db.query_one("SELECT user_id, password_hash FROM users WHERE email = %s", (email,))
            # Always check a hash, even for an unknown email, so both cases take the same time.
            valid = check_password_hash(user["password_hash"] if user else DUMMY_HASH, password)
            if user and valid:
                _failures.pop(email, None)
                _log_in(user["user_id"])
                return redirect(next_url or url_for("dashboard"))
            _record_failure(email)
            error = "Invalid email or password."
    return render_template("login.html", email=email, error=error, next_url=next_url), (401 if error else 200)


@auth.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("landing"))
