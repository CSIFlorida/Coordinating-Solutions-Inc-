"""
Authentication helpers: password hashing, session helpers, route decorators.

NOTE ON SMS TWO-FACTOR AUTH: the original spec calls for phone + SMS code
login. Sending real SMS requires a paid third-party provider (e.g. Twilio)
tied to the agency's own account — that's not something this app can wire
up without your credentials. What's implemented now is real, secure
phone + password login (passwords are hashed, never stored in plain text).
When you're ready to add SMS verification, this is the one place
(`login()` in app.py) that would call out to a provider like Twilio to text
a one-time code before completing login — everything else stays the same.
"""
import re
from datetime import datetime
from functools import wraps

from flask import session, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash

from db import conn_ctx


def normalize_phone(phone):
    """Keep digits only, so '(305) 123-4567' and '3051234567' match."""
    return re.sub(r"\D", "", phone or "")


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, password_hash):
    if not password_hash:
        return False
    return check_password_hash(password_hash, password)


def get_user_by_phone(conn, phone):
    return conn.execute(
        "SELECT * FROM users WHERE phone=?", (normalize_phone(phone),)
    ).fetchone()


def create_user(conn, phone, password, display_name, role, worker_code=None):
    conn.execute(
        """INSERT INTO users (phone, password_hash, display_name, role, worker_code, created_at)
           VALUES (?,?,?,?,?,?)""",
        (normalize_phone(phone), hash_password(password), display_name, role,
         worker_code, datetime.utcnow().isoformat()),
    )


def any_users_exist():
    with conn_ctx() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        return row["n"] > 0


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    with conn_ctx() as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def manager_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if session.get("role") != "manager":
            flash("That page is for managers only.", "error")
            return redirect(url_for("worker_home"))
        return fn(*args, **kwargs)
    return wrapper
