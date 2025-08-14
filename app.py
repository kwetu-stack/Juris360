import os
import sqlite3
from pathlib import Path
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session
)

# =========================
# Config (env-driven)
# =========================
DATA_DIR = os.environ.get("DATA_DIR", ".")            # e.g., /data in Docker
DB_NAME = os.path.join(DATA_DIR, "juris360.db")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "kwetutech00")

app = Flask(__name__)
app.secret_key = SECRET_KEY

# =========================
# DB helpers
# =========================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create tables if they don't exist (safe to call repeatedly)."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

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

        cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            filename TEXT
        )
        """)

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
# (Your Docker CMD also runs prestart.py first, which calls init/seed again safely.)
if not os.path.exists(DB_NAME):
    init_db()
seed_admin()

# =========================
# Auth helpers
# =========================
def require_login():
    if "user" not in session:
        return redirect(url_for("login"))
    return None

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

@app.route("/documents")
def documents():
    redir = require_login()
    if redir: return redir
    with get_db() as conn:
        docs = conn.execute("SELECT id, title, filename FROM documents ORDER BY id DESC").fetchall()
    return render_template("documents.html", docs=docs)

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
    # helpful when running locally: ensure DB and admin exist
    init_db()
    seed_admin()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
