import os
import sqlite3
import mimetypes
from datetime import datetime
from pathlib import Path
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session,
    send_from_directory, abort, Response
)
from werkzeug.utils import secure_filename

# =========================
# Config (env-driven)
# =========================
DATA_DIR = os.environ.get("DATA_DIR", ".")  # e.g., /data in Docker
DB_NAME = os.path.join(DATA_DIR, "juris360.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "kwetutech00")

# uploads
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg"}

app = Flask(__name__)
app.secret_key = SECRET_KEY

# =========================
# DB helpers
# =========================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def _ensure_columns(conn, table, needed_cols_sql):
    """Add columns to an existing table if they don't exist (SQLite)."""
    have = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for col_sql in needed_cols_sql:
        col_name = col_sql.split()[0]
        if col_name not in have:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_sql}")

def init_db():
    """Create tables if they don't exist (safe to call repeatedly)."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)

    with get_db() as conn:
        cur = conn.cursor()

        # users (plaintext for boilerplate; hash in real apps)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT,
            email TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            title TEXT,
            description TEXT,
            status TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            description TEXT,
            type TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT,
            amount REAL,
            status TEXT
        )
        """)

        # base documents table (your original)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            filename TEXT
        )
        """)

        # add only the extra columns your current documents.html uses
        _ensure_columns(conn, "documents", [
            "case_id TEXT",
            "doc_type TEXT",
            "notes TEXT",
            "uploaded_at TEXT",
            "size_bytes INTEGER"
        ])

        conn.commit()

def seed_admin():
    """Ensure admin user exists with the configured password."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username=?", (ADMIN_USER,))
        row = cur.fetchone()
        if not row:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (?,?)",
                (ADMIN_USER, ADMIN_PASS)
            )
        elif row["password"] != ADMIN_PASS:
            cur.execute(
                "UPDATE users SET password=? WHERE username=?",
                (ADMIN_PASS, ADMIN_USER)
            )
        conn.commit()

# Ensure DB exists when the module loads (works locally and on Render).
if not os.path.exists(DB_NAME):
    init_db()
else:
    Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
seed_admin()

# =========================
# Small helpers
# =========================
def require_login():
    if "user" not in session:
        return redirect(url_for("login"))
    return None

def allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS

def human_size(n: int) -> str:
    try:
        n = int(n or 0)
    except Exception:
        n = 0
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024 or unit == "TB":
            return f"{n} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0

# =========================
# Routes
# =========================
@app.route("/")
def home():
    # redirect to dashboard if logged in, else to login
    return redirect(url_for("dashboard") if "user" in session else url_for("login"))

# ---- Auth ----
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = (request.form.get("username") or "").strip()
        pw   = (request.form.get("password") or "").strip()

        # Check env-admin first (fast path)
        if user == ADMIN_USER and pw == ADMIN_PASS:
            session["user"] = user
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))

        # Fallback: check DB users
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username=? AND password=?", (user, pw))
            if cur.fetchone():
                session["user"] = user
                flash("Login successful!", "success")
                return redirect(url_for("dashboard"))

        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# ---- Core pages ----
@app.route("/dashboard")
def dashboard():
    redir = require_login()
    if redir: return redir
    return render_template("dashboard.html", user=session["user"])

@app.route("/view-clients")
def view_clients():
    redir = require_login()
    if redir: return redir
    with get_db() as conn:
        clients = conn.execute(
            "SELECT id, name, contact, email FROM clients ORDER BY id DESC"
        ).fetchall()
    return render_template("view-clients.html", clients=clients)

@app.route("/add-client", methods=["GET", "POST"])
def add_client():
    redir = require_login()
    if redir: return redir

    if request.method == "POST":
        name    = (request.form.get("client_name") or request.form.get("name") or "").strip()
        contact = (request.form.get("phone") or request.form.get("contact") or "").strip()
        email   = (request.form.get("email") or "").strip()

        if not name:
            flash("Client name is required.", "danger")
            return render_template("add-client.html")

        with get_db() as conn:
            conn.execute(
                "INSERT INTO clients (name, contact, email) VALUES (?,?,?)",
                (name, contact, email)
            )
            conn.commit()

        flash("Client added successfully!", "success")
        return redirect(url_for("view_clients"))

    return render_template("add-client.html")

@app.route("/view-cases")
def view_cases():
    redir = require_login()
    if redir: return redir
    with get_db() as conn:
        cases = conn.execute("""
            SELECT cases.id, cases.title, cases.description, cases.status,
                   clients.name AS client_name
            FROM cases
            LEFT JOIN clients ON cases.client_id = clients.id
            ORDER BY cases.id DESC
        """).fetchall()
    return render_template("view-cases.html", cases=cases)

@app.route("/add-case", methods=["GET", "POST"])
def add_case():
    redir = require_login()
    if redir: return redir

    if request.method == "POST":
        title       = (request.form.get("title") or request.form.get("case_id") or "").strip()
        description = (request.form.get("description") or "").strip()
        status      = (request.form.get("status") or "Open").strip() or "Open"

        client_id = (request.form.get("client_id") or "").strip()
        client_name = (request.form.get("client_name") or "").strip()

        if not title:
            flash("Case title is required.", "danger")
            # also show clients for the dropdown
            with get_db() as conn:
                clients = conn.execute("SELECT id, name FROM clients ORDER BY name ASC").fetchall()
            return render_template("add-case.html", clients=clients)

        with get_db() as conn:
            cur = conn.cursor()
            # If no client_id but a client_name was provided, create client on the fly
            if not client_id and client_name:
                cur.execute("INSERT INTO clients (name) VALUES (?)", (client_name,))
                client_id = cur.lastrowid

            cur.execute("""
                INSERT INTO cases (client_id, title, description, status)
                VALUES (?,?,?,?)
            """, (client_id if client_id else None, title, description, status))
            conn.commit()

        flash("Case added successfully!", "success")
        return redirect(url_for("view_cases"))

    # GET -> show form with clients list
    with get_db() as conn:
        clients = conn.execute("SELECT id, name FROM clients ORDER BY name ASC").fetchall()
    return render_template("add-case.html", clients=clients)

# ---- Optional pages (wired to your templates) ----
@app.route("/schedule")
def schedule():
    redir = require_login()
    if redir: return redir
    with get_db() as conn:
        events = conn.execute("SELECT date, description, type FROM schedule ORDER BY date ASC").fetchall()
    return render_template("schedule.html", events=events)

@app.route("/billing", methods=["GET", "POST"])
def billing():
    redir = require_login()
    if redir: return redir

    if request.method == "POST":
        client = (request.form.get("client_name") or "").strip()
        status = (request.form.get("status") or "Unpaid").strip() or "Unpaid"
        try:
            amount = float(request.form.get("amount") or 0)
        except ValueError:
            amount = 0.0
        with get_db() as conn:
            conn.execute(
                "INSERT INTO billing (client, amount, status) VALUES (?,?,?)",
                (client, amount, status)
            )
            conn.commit()
        flash("Invoice saved.", "success")
        return redirect(url_for("billing"))

    with get_db() as conn:
        bills = conn.execute("SELECT client, amount, status FROM billing ORDER BY id DESC").fetchall()
    return render_template("billing.html", bills=bills)

# -------- Documents: list / upload / preview / download / delete --------
@app.route("/documents")
def documents():
    redir = require_login()
    if redir: return redir
    # fetch all, but your current documents.html uses `documents` (not `docs`)
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, title, filename, case_id, doc_type, notes, uploaded_at, size_bytes
            FROM documents
            ORDER BY id DESC
        """).fetchall()

    documents = []
    for r in rows:
        documents.append({
            "id": r["id"],
            "filename": r["filename"],
            "case_id": r["case_id"],
            "doc_type": r["doc_type"],
            "notes": r["notes"],
            "uploaded_at": r["uploaded_at"] or "",
            "size_human": human_size(r["size_bytes"])
        })
    return render_template("documents.html", documents=documents, docs=rows)

@app.route("/documents/upload", methods=["POST"])
def upload_document():
    redir = require_login()
    if redir: return redir

    file = request.files.get("file")
    case_id = (request.form.get("case_id") or "").strip()
    doc_type = (request.form.get("doc_type") or "").strip()
    notes = (request.form.get("notes") or "").strip()

    if not file or not file.filename.strip():
        flash("Please choose a file to upload.", "error")
        return redirect(url_for("documents"))

    filename = secure_filename(file.filename)
    if not allowed_file(filename):
        flash("File type not allowed.", "error")
        return redirect(url_for("documents"))

    dest = os.path.join(UPLOADS_DIR, filename)
    base, ext = os.path.splitext(filename)
    i = 1
    while os.path.exists(dest):  # avoid overwriting
        filename = f"{base}_{i}{ext}"
        dest = os.path.join(UPLOADS_DIR, filename)
        i += 1

    file.save(dest)
    size_bytes = os.path.getsize(dest)
    uploaded_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as conn:
        conn.execute("""
            INSERT INTO documents (title, filename, case_id, doc_type, notes, uploaded_at, size_bytes)
            VALUES (?,?,?,?,?,?,?)
        """, (filename, filename, case_id, doc_type, notes, uploaded_at, size_bytes))
        conn.commit()

    flash("Document uploaded successfully.", "success")
    return redirect(url_for("documents"))

@app.route("/documents/<int:doc_id>/download")
def download_document(doc_id):
    redir = require_login()
    if redir: return redir
    with get_db() as conn:
        row = conn.execute("SELECT filename FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        abort(404)
    return send_from_directory(UPLOADS_DIR, row["filename"], as_attachment=True)

@app.route("/documents/<int:doc_id>/preview")
def preview_document(doc_id):
    redir = require_login()
    if redir: return redir
    with get_db() as conn:
        row = conn.execute("SELECT filename FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        abort(404)

    filename = row["filename"]
    path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(path):
        abort(404)

    mime, _ = mimetypes.guess_type(filename)
    mime = mime or "application/octet-stream"
    with open(path, "rb") as f:
        data = f.read()
    return Response(
        data,
        mimetype=mime,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

@app.route("/documents/<int:doc_id>/delete", methods=["POST"])
def delete_document(doc_id):
    redir = require_login()
    if redir: return redir
    with get_db() as conn:
        row = conn.execute("SELECT filename FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not row:
            flash("Document not found.", "error")
            return redirect(url_for("documents"))
        filename = row["filename"]
        conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        conn.commit()

    try:
        os.remove(os.path.join(UPLOADS_DIR, filename))
    except FileNotFoundError:
        pass

    flash("Document deleted.", "success")
    return redirect(url_for("documents"))

@app.route("/reports")
def reports():
    redir = require_login()
    if redir: return redir
    return render_template("reports.html")

@app.route("/settings")
def settings():
    redir = require_login()
    if redir: return redir
    return render_template("settings.html")

# =========================
# Dev entrypoint (ignored by Gunicorn)
# =========================
if __name__ == "__main__":
    init_db()
    seed_admin()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
