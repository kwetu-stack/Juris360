import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session

# =========================
# Config (env-driven)
# =========================
DATA_DIR = os.environ.get("DATA_DIR", ".")  # e.g., /opt/render/project/src/data on Render
os.makedirs(DATA_DIR, exist_ok=True)

DB_NAME = os.path.join(DATA_DIR, "juris360.db")

SECRET_KEY = os.environ.get("SECRET_KEY", "mysecret123")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "kwetutech00")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# =========================
# DB setup / helpers
# =========================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create tables if they don't exist (idempotent)."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL,
            contact TEXT,
            email   TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id   INTEGER,
            title       TEXT,
            description TEXT,
            status      TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    """)

    conn.commit()
    conn.close()

# Flask 3 removed before_first_request — initialize DB on import.
init_db()

def require_login():
    if "user" not in session:
        return redirect(url_for("login"))
    return None

# =========================
# Routes
# =========================
@app.route("/")
def index():
    if "user" in session:
        return render_template("dashboard.html", user=session["user"])
    return redirect(url_for("login"))

# alias for templates that call url_for('dashboard')
@app.route("/dashboard")
def dashboard():
    redir = require_login()
    if redir: return redir
    return render_template("dashboard.html", user=session["user"])

# ---- Auth ----
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = (request.form.get("username") or "").strip()
        pw   = (request.form.get("password") or "").strip()
        if user == ADMIN_USER and pw == ADMIN_PASS:
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

# ---- Clients ----
@app.route("/view-clients")
def view_clients():
    redir = require_login()
    if redir: return redir
    conn = get_db()
    clients = conn.execute(
        "SELECT id, name, contact, email FROM clients ORDER BY id DESC"
    ).fetchall()
    conn.close()
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

        conn = get_db()
        conn.execute(
            "INSERT INTO clients (name, contact, email) VALUES (?, ?, ?)",
            (name, contact, email),
        )
        conn.commit()
        conn.close()
        flash("Client added successfully!", "success")
        return redirect(url_for("view_clients"))

    return render_template("add-client.html")

# ---- Cases ----
@app.route("/view-cases")
def view_cases():
    redir = require_login()
    if redir: return redir
    conn = get_db()
    cases = conn.execute("""
        SELECT c.id, c.title, c.description, c.status,
               COALESCE(cl.name, '—') AS client_name
        FROM cases c
        LEFT JOIN clients cl ON c.client_id = cl.id
        ORDER BY c.id DESC
    """).fetchall()
    conn.close()
    return render_template("view-cases.html", cases=cases)

@app.route("/add-case", methods=["GET", "POST"])
def add_case():
    redir = require_login()
    if redir: return redir

    if request.method == "POST":
        title = (request.form.get("title") or request.form.get("case_id") or "").strip()
        description = (request.form.get("description") or "").strip()
        status = (request.form.get("status") or "Open").strip() or "Open"

        client_id = (request.form.get("client_id") or "").strip()
        if not client_id:
            client_name = (request.form.get("client_name") or "").strip()
            if not title or not client_name:
                flash("Title and Client are required.", "danger")
                return render_template("add-case.html", clients=_client_choices())
            conn = get_db()
            cur = conn.cursor()
            cur.execute("INSERT INTO clients (name) VALUES (?)", (client_name,))
            client_id = cur.lastrowid
            cur.execute(
                "INSERT INTO cases (client_id, title, description, status) VALUES (?,?,?,?)",
                (client_id, title, description, status),
            )
            conn.commit()
            conn.close()
        else:
            conn = get_db()
            conn.execute(
                "INSERT INTO cases (client_id, title, description, status) VALUES (?,?,?,?)",
                (client_id, title, description, status),
            )
            conn.commit()
            conn.close()

        flash("Case added successfully!", "success")
        return redirect(url_for("view_cases"))

    return render_template("add-case.html", clients=_client_choices())

def _client_choices():
    conn = get_db()
    clients = conn.execute("SELECT id, name FROM clients ORDER BY name ASC").fetchall()
    conn.close()
    return clients

# ---- Other pages (stubs) ----
@app.route("/reports")
def reports():
    redir = require_login()
    if redir: return redir
    return render_template("reports.html")

@app.route("/documents")
def documents():
    redir = require_login()
    if redir: return redir
    return render_template("documents.html")

@app.route("/settings")
def settings():
    redir = require_login()
    if redir: return redir
    return render_template("settings.html")

# Health check (optional but useful)
@app.route("/healthz")
def healthz():
    return "ok", 200

# =========================
# Main (dev only)
# =========================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
