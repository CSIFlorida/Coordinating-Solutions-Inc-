"""
CSI Visit Tracking System — standalone Flask app (mobile-friendly web app).

Run locally:
    pip install -r requirements.txt
    python3 import_consumers.py "/path/to/EMedi Stats ... WORKING DOC.xlsx"
    python3 app.py
    # open http://localhost:5000 on a phone or desktop browser
"""
import os
from datetime import date, datetime
from collections import defaultdict

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename

from db import conn_ctx, init_db
import due_dates as dd
from areas import area_label
import auth

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

HERE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(HERE, "data", "uploads")
MONTH_NAMES = dd.MONTH_NAMES


def current_year_month():
    today = date.today()
    return today.year, today.month - 1


# ---------------------------------------------------------------- Splash / Auth

@app.route("/")
def splash():
    if session.get("user_id"):
        return redirect(url_for("after_login_redirect"))
    return render_template("splash.html", first_run=not auth.any_users_exist())


@app.route("/after-login")
def after_login_redirect():
    if session.get("role") == "manager":
        return redirect(url_for("manager_dashboard"))
    return redirect(url_for("worker_home"))


@app.route("/setup", methods=["GET", "POST"])
def setup():
    """First-run only: create the initial Manager account."""
    if auth.any_users_exist():
        return redirect(url_for("login"))
    if request.method == "POST":
        phone = request.form.get("phone", "")
        password = request.form.get("password", "")
        display_name = request.form.get("display_name", "Manager").strip() or "Manager"
        if not phone or len(password) < 6:
            flash("Enter a phone number and a password of at least 6 characters.", "error")
            return render_template("setup.html")
        with conn_ctx() as conn:
            auth.create_user(conn, phone, password, display_name, role="manager")
        flash("Manager account created. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("setup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if not auth.any_users_exist():
        return redirect(url_for("setup"))
    if request.method == "POST":
        phone = request.form.get("phone", "")
        password = request.form.get("password", "")
        with conn_ctx() as conn:
            user = auth.get_user_by_phone(conn, phone)
            if user and auth.verify_password(password, user["password_hash"]):
                conn.execute("UPDATE users SET last_login_at=? WHERE id=?",
                             (datetime.utcnow().isoformat(), user["id"]))
                session["user_id"] = user["id"]
                session["role"] = user["role"]
                session["display_name"] = user["display_name"]
                session["worker_code"] = user["worker_code"]
                return redirect(url_for("after_login_redirect"))
        flash("Phone number or password is incorrect.", "error")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Worker self-registration against an existing worker_code."""
    with conn_ctx() as conn:
        taken = {r["worker_code"] for r in conn.execute(
            "SELECT worker_code FROM users WHERE worker_code IS NOT NULL")}
        all_codes = [r["worker_code"] for r in conn.execute(
            "SELECT worker_code FROM worker_directory ORDER BY worker_code")]
        available_codes = [c for c in all_codes if c not in taken]

    if request.method == "POST":
        worker_code = request.form.get("worker_code", "")
        phone = request.form.get("phone", "")
        password = request.form.get("password", "")
        display_name = request.form.get("display_name", "").strip()
        if worker_code not in available_codes:
            flash("Please select a valid, unclaimed worker code.", "error")
            return render_template("signup.html", codes=available_codes)
        if not phone or len(password) < 6 or not display_name:
            flash("Fill in your name, phone, and a password of at least 6 characters.", "error")
            return render_template("signup.html", codes=available_codes)
        with conn_ctx() as conn:
            if auth.get_user_by_phone(conn, phone):
                flash("That phone number is already registered.", "error")
                return render_template("signup.html", codes=available_codes)
            auth.create_user(conn, phone, password, display_name, role="worker", worker_code=worker_code)
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html", codes=available_codes)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("splash"))


# ---------------------------------------------------------------- Worker UI

def build_worker_due_list(conn, worker_code, year, month0):
    consumers = conn.execute(
        "SELECT * FROM consumers WHERE active=1 AND worker_code=?", (worker_code,)
    ).fetchall()
    completions = {
        (r["consumer_id"], r["visit_type"]): r
        for r in conn.execute(
            "SELECT * FROM visit_records WHERE due_year=? AND due_month=?",
            (year, month0 + 1),
        ).fetchall()
    }
    items = []
    for c in consumers:
        flags = dd.due_flags(c["effective_date"], c["gh"], c["il"], year, month0)
        due_types = [k for k in ("sp", "quarterly", "monthly") if flags[k]]
        if not due_types:
            continue
        # a consumer may be due for more than one type in edge cases; show once,
        # using the highest-priority type for the card label
        priority = ["sp", "monthly", "quarterly"]
        primary_type = next((t for t in priority if t in due_types), due_types[0])
        comp = completions.get((c["id"], primary_type))
        item = dict(c)
        item["visit_type"] = primary_type
        item["visit_type_label"] = {"sp": "Support Plan", "quarterly": "Quarterly", "monthly": "Monthly"}[primary_type]
        item["completion"] = dict(comp) if comp else None
        item["is_done"] = bool(comp and comp["status"] == "completed")
        items.append(item)
    items.sort(key=lambda x: (x["is_done"], x["name"] or ""))
    return items


@app.route("/worker/home")
@auth.login_required
def worker_home():
    worker_code = session.get("worker_code")
    year, month0 = current_year_month()
    with conn_ctx() as conn:
        items = build_worker_due_list(conn, worker_code, year, month0)
    done_count = sum(1 for i in items if i["is_done"])
    return render_template(
        "worker_home.html", items=items, done_count=done_count, total_count=len(items),
        month_label=f"{MONTH_NAMES[month0]} {year}", area_label=area_label,
        active_tab="home",
    )


@app.route("/worker/consumer/<int:consumer_id>")
@auth.login_required
def consumer_detail(consumer_id):
    year, month0 = current_year_month()
    with conn_ctx() as conn:
        consumer = conn.execute("SELECT * FROM consumers WHERE id=?", (consumer_id,)).fetchone()
        if not consumer or (session.get("role") == "worker" and consumer["worker_code"] != session.get("worker_code")):
            flash("Consumer not found or not assigned to you.", "error")
            return redirect(url_for("worker_home"))
        flags = dd.due_flags(consumer["effective_date"], consumer["gh"], consumer["il"], year, month0)
        priority = ["sp", "monthly", "quarterly"]
        due_types = [t for t in priority if flags[t]]
        primary_type = due_types[0] if due_types else "quarterly"
        history = conn.execute(
            """SELECT vr.*, u.display_name AS submitted_by_name FROM visit_records vr
               LEFT JOIN users u ON u.id = vr.submitted_by
               WHERE vr.consumer_id=? ORDER BY vr.due_year DESC, vr.due_month DESC""",
            (consumer_id,),
        ).fetchall()
    return render_template(
        "consumer_detail.html", consumer=consumer, primary_type=primary_type,
        year=year, month0=month0, history=history, area_label=area_label,
        visit_type_label={"sp": "Support Plan", "quarterly": "Quarterly", "monthly": "Monthly"},
        active_tab="home",
    )


@app.route("/worker/consumer/<int:consumer_id>/submit", methods=["POST"])
@auth.login_required
def submit_visit(consumer_id):
    visit_type = request.form.get("visit_type", "quarterly")
    due_year = int(request.form.get("due_year"))
    due_month = int(request.form.get("due_month"))
    note = request.form.get("note", "").strip()
    completed_date = request.form.get("completed_date") or date.today().isoformat()

    with conn_ctx() as conn:
        conn.execute(
            """INSERT INTO visit_records
               (consumer_id, visit_type, due_year, due_month, status, completed_date, note, submitted_by, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(consumer_id, visit_type, due_year, due_month) DO UPDATE SET
                 status='completed', completed_date=excluded.completed_date,
                 note=excluded.note, submitted_by=excluded.submitted_by, updated_at=excluded.updated_at""",
            (consumer_id, visit_type, due_year, due_month, "completed", completed_date,
             note, session.get("user_id"), datetime.utcnow().isoformat()),
        )
    return redirect(url_for("celebrate", consumer_id=consumer_id))


@app.route("/worker/celebrate/<int:consumer_id>")
@auth.login_required
def celebrate(consumer_id):
    with conn_ctx() as conn:
        consumer = conn.execute("SELECT * FROM consumers WHERE id=?", (consumer_id,)).fetchone()
    return render_template("celebrate.html", consumer=consumer)


@app.route("/worker/visits")
@auth.login_required
def worker_visits():
    with conn_ctx() as conn:
        rows = conn.execute(
            """SELECT vr.*, c.name AS consumer_name FROM visit_records vr
               JOIN consumers c ON c.id = vr.consumer_id
               WHERE vr.submitted_by=?
               ORDER BY vr.updated_at DESC LIMIT 200""",
            (session.get("user_id"),),
        ).fetchall()
    return render_template("worker_visits.html", rows=rows, active_tab="visits")


@app.route("/worker/profile")
@auth.login_required
def worker_profile():
    return render_template("worker_profile.html", active_tab="profile")


# ---------------------------------------------------------------- Manager UI

@app.route("/manager/dashboard")
@auth.manager_required
def manager_dashboard():
    year, month0 = current_year_month()
    with conn_ctx() as conn:
        total_consumers = conn.execute("SELECT COUNT(*) n FROM consumers WHERE active=1").fetchone()["n"]
        total_workers = conn.execute("SELECT COUNT(*) n FROM worker_directory").fetchone()["n"]
        consumers = conn.execute("SELECT * FROM consumers WHERE active=1").fetchall()
        completions = {
            (r["consumer_id"], r["visit_type"]): r
            for r in conn.execute(
                "SELECT * FROM visit_records WHERE due_year=? AND due_month=?",
                (year, month0 + 1),
            ).fetchall()
        }
        due_total, done_total = 0, 0
        area_stats = defaultdict(lambda: {"due": 0, "done": 0})
        for c in consumers:
            flags = dd.due_flags(c["effective_date"], c["gh"], c["il"], year, month0)
            for key in ("sp", "quarterly", "monthly"):
                if flags[key]:
                    due_total += 1
                    area_stats[c["area"]]["due"] += 1
                    comp = completions.get((c["id"], key))
                    if comp and comp["status"] == "completed":
                        done_total += 1
                        area_stats[c["area"]]["done"] += 1
        last_upload = conn.execute(
            "SELECT * FROM data_uploads ORDER BY id DESC LIMIT 1"
        ).fetchone()

    return render_template(
        "manager_dashboard.html", total_consumers=total_consumers, total_workers=total_workers,
        due_total=due_total, done_total=done_total, area_stats=dict(area_stats),
        area_label=area_label, month_label=f"{MONTH_NAMES[month0]} {year}",
        last_upload=last_upload, active_tab="dashboard",
    )


@app.route("/manager/upload", methods=["GET", "POST"])
@auth.manager_required
def manager_upload():
    with conn_ctx() as conn:
        history = conn.execute("SELECT * FROM data_uploads ORDER BY id DESC LIMIT 20").fetchall()

    if request.method == "POST":
        f = request.files.get("file")
        if not f or not f.filename.lower().endswith((".xlsx", ".xls")):
            flash("Please choose a .xlsx file to upload.", "error")
            return redirect(url_for("manager_upload"))
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        path = os.path.join(UPLOAD_DIR, secure_filename(f.filename))
        f.save(path)
        import import_consumers
        import_consumers.import_file(path, uploaded_by=session.get("user_id"))
        flash("Data uploaded and imported successfully.", "success")
        return redirect(url_for("manager_upload"))

    return render_template("manager_upload.html", history=history, active_tab="upload")


@app.route("/manager/reports")
@auth.manager_required
def manager_reports():
    year = int(request.args.get("year", current_year_month()[0]))
    month0 = int(request.args.get("month", current_year_month()[1]))
    area = request.args.get("area", "ALL")

    with conn_ctx() as conn:
        q = "SELECT * FROM consumers WHERE active=1"
        params = []
        if area != "ALL":
            q += " AND area=?"
            params.append(area)
        consumers = conn.execute(q, params).fetchall()
        completions = {
            (r["consumer_id"], r["visit_type"]): r
            for r in conn.execute(
                "SELECT * FROM visit_records WHERE due_year=? AND due_month=?",
                (year, month0 + 1),
            ).fetchall()
        }

    groups = {"sp": [], "quarterly": [], "monthly": []}
    for c in consumers:
        flags = dd.due_flags(c["effective_date"], c["gh"], c["il"], year, month0)
        for key in ("sp", "quarterly", "monthly"):
            if flags[key]:
                comp = completions.get((c["id"], key))
                item = dict(c)
                item["completion"] = dict(comp) if comp else None
                groups[key].append(item)

    return render_template(
        "manager_reports.html", groups=groups, year=year, month0=month0, area=area,
        month_names=MONTH_NAMES, years=range(date.today().year - 1, date.today().year + 3),
        area_label=area_label, active_tab="reports",
    )


@app.route("/manager/reports/export")
@auth.manager_required
def manager_reports_export():
    import csv
    import io

    year = int(request.args.get("year", current_year_month()[0]))
    month0 = int(request.args.get("month", current_year_month()[1]))
    area = request.args.get("area", "ALL")
    fmt = request.args.get("fmt", "csv")

    with conn_ctx() as conn:
        q = "SELECT * FROM consumers WHERE active=1"
        params = []
        if area != "ALL":
            q += " AND area=?"
            params.append(area)
        consumers = conn.execute(q, params).fetchall()
        completions = {
            (r["consumer_id"], r["visit_type"]): r
            for r in conn.execute(
                "SELECT * FROM visit_records WHERE due_year=? AND due_month=?",
                (year, month0 + 1),
            ).fetchall()
        }

    rows = []
    for c in consumers:
        flags = dd.due_flags(c["effective_date"], c["gh"], c["il"], year, month0)
        for key in ("sp", "quarterly", "monthly"):
            if flags[key]:
                comp = completions.get((c["id"], key))
                rows.append({
                    "name": c["name"], "worker_code": c["worker_code"], "area": area_label(c["area"]),
                    "visit_type": {"sp": "Support Plan", "quarterly": "Quarterly", "monthly": "Monthly"}[key],
                    "status": "Completed" if comp and comp["status"] == "completed" else "Pending",
                    "address": c["address"], "city": c["city"], "zip": c["zip"], "phone": c["phone"],
                    "health_manager": c["health_manager"],
                })

    month_label = f"{MONTH_NAMES[month0]}_{year}"

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else
                                 ["name", "worker_code", "area", "visit_type", "status", "address", "city", "zip", "phone", "health_manager"])
        writer.writeheader()
        writer.writerows(rows)
        from flask import Response
        return Response(
            buf.getvalue(), mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=visit_report_{month_label}.csv"},
        )

    # PDF
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    import io as _io

    buf = _io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                             leftMargin=0.7 * inch, rightMargin=0.7 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("T", parent=styles["Title"], fontSize=16)
    sub_style = ParagraphStyle("S", parent=styles["Normal"], fontSize=10, textColor=colors.grey, spaceAfter=14)
    name_style = ParagraphStyle("N", parent=styles["Normal"], fontSize=11, fontName="Helvetica-Bold")
    meta_style = ParagraphStyle("M", parent=styles["Normal"], fontSize=8, textColor=colors.grey, spaceAfter=8)

    story = [Paragraph(f"Visit Due Report &ndash; {area_label(area) if area != 'ALL' else 'All Areas'}", title_style),
             Paragraph(f"{MONTH_NAMES[month0]} {year}", sub_style)]
    for row in rows:
        story.append(Paragraph(f"{row['name']} ({row['worker_code']}) &mdash; {row['visit_type']} &mdash; {row['status']}", name_style))
        story.append(Paragraph(
            f"{row['address']}, {row['city']} {row['zip']} | Phone: {row['phone'] or '—'} | Health Manager: {row['health_manager'] or '—'}",
            meta_style))
    if not rows:
        story.append(Paragraph("No consumers due for this selection.", meta_style))
    doc.build(story)
    buf.seek(0)
    from flask import Response
    return Response(
        buf.read(), mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=visit_report_{month_label}.pdf"},
    )


@app.route("/manager/workers")
@auth.manager_required
def manager_workers():
    year, month0 = current_year_month()
    with conn_ctx() as conn:
        workers = conn.execute("SELECT * FROM worker_directory ORDER BY worker_code").fetchall()
        users_by_code = {u["worker_code"]: u for u in conn.execute(
            "SELECT * FROM users WHERE role='worker'").fetchall()}
        consumers = conn.execute("SELECT * FROM consumers WHERE active=1").fetchall()
        completions = {
            (r["consumer_id"], r["visit_type"]): r
            for r in conn.execute(
                "SELECT * FROM visit_records WHERE due_year=? AND due_month=?",
                (year, month0 + 1),
            ).fetchall()
        }

    stats = defaultdict(lambda: {"assigned": 0, "due": 0, "done": 0})
    for c in consumers:
        stats[c["worker_code"]]["assigned"] += 1
        flags = dd.due_flags(c["effective_date"], c["gh"], c["il"], year, month0)
        for key in ("sp", "quarterly", "monthly"):
            if flags[key]:
                stats[c["worker_code"]]["due"] += 1
                comp = completions.get((c["id"], key))
                if comp and comp["status"] == "completed":
                    stats[c["worker_code"]]["done"] += 1

    rows = []
    for w in workers:
        s = stats.get(w["worker_code"], {"assigned": 0, "due": 0, "done": 0})
        linked_user = users_by_code.get(w["worker_code"])
        rows.append({
            "worker_code": w["worker_code"],
            "has_account": linked_user is not None,
            "display_name": linked_user["display_name"] if linked_user is not None else None,
            **s,
        })

    return render_template("manager_workers.html", rows=rows, month_label=f"{MONTH_NAMES[month0]} {year}",
                            active_tab="workers")


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
