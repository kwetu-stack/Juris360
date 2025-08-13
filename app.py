import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory

# =========================
# Config (env-driven)
# =========================
DATA_DIR = os.environ.get("DATA_DIR", ".")  # e.g. /var/data on Render disk
os.makedirs(DATA_DIR, exist_ok=True)

DB_NAME = os.path.join(DATA_DIR, "juris360.db")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "kwetutech001")

app = Flask(__name__)
app.secret_key = SECRET_KEY


# =========================
# DB setup / helpers
# =========================
def init_db():
    """Create tables if they don't exist."""
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()

        # Users (plaintext for boilerplate simplicity — switch to hashing later)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        """)

        # Cases (minimal schema compatible with templates)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cases(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,          -- we store case_id/title in this field
                client TEXT,
                status TEXT
            )
        """)

        # Clients (minimal schema compatible with templates)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clients(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                contact TEXT,
                email TEXT
            )
        """)

        # Schedule (demo)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedule(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                description TEXT,
                type TEXT
            )
        """)

        # Billing (demo)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS billing(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client TEXT,
                amount REAL,
                status TEXT
            )
        """)

        # Documents (demo stubs)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                filename TEXT
            )
        """)

        conn.commit()


def seed_admin():
    """Ensure the admin user exists and has the desired password (UPSERT)."""
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        # Works on SQLite 3.24+ (Render images support this)
        cur.execute("""
            INSERT INTO users (username, password)
            VALUES (?, ?)
            ON CONFLICT(username) DO UPDATE SET password=excluded.password
        """, (ADMIN_USER, ADMIN_PASS))
        conn.commit()


def is_logged_in():
    return "username" in session


def require_login():
    if not is_logged_in():
        return redirect(url_for("login"))
    return None


# Ensure DB exists & admin is seeded when module is imported (important for Gunicorn/Render)
if not os.path.exists(DB_NAME):
    init_db()
seed_admin()


# =========================
# Routes
# =========================
@app.route("/")
def home():
    return redirect(url_for("dashboard") if is_logged_in() else url_for("login"))


# Optional: quiet the favicon 404s
@app.route("/favicon.ico")
def favicon():
    # Place a favicon.ico in /static if you want a real icon
    static_path = os.path.join("static", "favicon.ico")
    if os.path.exists(static_path):
        return send_from_directory("static", "favicon.ico")
    # Return a tiny empty response if no favicon available
    return ("", 204)


# ---- Auth ----
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Accept both "username" and "email" field names from the form
        username = (request.form.get("username") or request.form.get("email") or "").strip()
        password = (request.form.get("password") or "").strip()
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username=? AND password=?", (username, password))
            ok = cur.fetchone()
        if ok:
            session["username"] = username
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---- Pages ----
@app.route("/dashboard")
def dashboard():
    redir = require_login()
    if redir: return redir
    return render_template("dashboard.html")


@app.route("/view-cases")
def view_cases():
    redir = require_login()
    if redir: return redir
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, client, status FROM cases ORDER BY id DESC")
        cases = cur.fetchall()
    return render_template("view-cases.html", cases=cases)


@app.route("/view-clients")
def view_clients():
    redir = require_login()
    if redir: return redir
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, contact, email FROM clients ORDER BY id DESC")
        clients = cur.fetchall()
    return render_template("view-clients.html", clients=clients)


@app.route("/schedule")
def schedule():
    redir = require_login()
    if redir: return redir
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT date, description, type FROM schedule ORDER BY date ASC")
        events = cur.fetchall()
    return render_template("schedule.html", events=events)


@app.route("/billing", methods=["GET", "POST"])
def billing():
    redir = require_login()
    if redir: return redir

    # Minimal POST handler for the modal in billing.html
    if request.method == "POST":
        client_name = (request.form.get("client_name") or "").strip()
        status = (request.form.get("status") or "Unpaid").strip() or "Unpaid"
        try:
            amount_val = float(request.form.get("amount") or 0)
        except ValueError:
            amount_val = 0.0
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO billing (client, amount, status) VALUES (?,?,?)",
                        (client_name, amount_val, status))
            conn.commit()
        flash("Invoice saved (minimal record).", "success")
        return redirect(url_for("billing"))

    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT client, amount, status FROM billing ORDER BY id DESC")
        bills = cur.fetchall()
    return render_template("billing.html", bills=bills)


@app.route("/documents")
def documents():
    redir = require_login()
    if redir: return redir
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, filename FROM documents ORDER BY id DESC")
        docs = cur.fetchall()
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


# ---- Add Case (matches add-case.html) ----
@app.route("/add-case", methods=["GET", "POST"])
def add_case():
    redir = require_login()
    if redir: return redir

    if request.method == "POST":
        # Map rich form fields to simple schema
        title = (request.form.get("title") or request.form.get("case_id") or "").strip()
        client_name = (request.form.get("client_name") or "").strip()
        status = (request.form.get("status") or "Open").strip() or "Open"

        if not title or not client_name:
            flash("Title and Client are required.", "error")
            return render_template("add-case.html")

        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO cases (title, client, status) VALUES (?,?,?)",
                        (title, client_name, status))
            conn.commit()

        flash("Case saved.", "success")
        return redirect(url_for("view_cases"))

    return render_template("add-case.html")


# ---- Add Client (matches add-client.html) ----
@app.route("/add-client", methods=["GET", "POST"])
def add_client():
    redir = require_login()
    if redir: return redir

    if request.method == "POST":
        client_name = (request.form.get("client_name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip()

        if not client_name:
            flash("Client name is required.", "error")
            return render_template("add-client.html")

        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO clients (name, contact, email) VALUES (?,?,?)",
                        (client_name, phone, email))
            conn.commit()

        flash("Client added successfully!", "success")
        return redirect(url_for("view_clients"))

    return render_template("add-client.html")


# ---- Stubs so template links don't 404 (wire up later if needed) ----
@app.route("/documents/upload", methods=["POST"])
def upload_document():
    redir = require_login()
    if redir: return redir
    flash("Upload handling not implemented in minimal app.py yet.", "error")
    return redirect(url_for("documents"))

@app.route("/documents/download/<int:doc_id>")
def download_document(doc_id):
    redir = require_login()
    if redir: return redir
    flash("Download handling not implemented in minimal app.py yet.", "error")
    return redirect(url_for("documents"))

@app.route("/documents/preview/<int:doc_id>")
def preview_document(doc_id):
    redir = require_login()
    if redir: return redir
    flash("Preview handling not implemented in minimal app.py yet.", "error")
    return redirect(url_for("documents"))

@app.route("/documents/delete/<int:doc_id>", methods=["POST"])
def delete_document(doc_id):
    redir = require_login()
    if redir: return redir
    flash("Delete handling not implemented in minimal app.py yet.", "error")
    return redirect(url_for("documents"))

@app.route("/settings/update", methods=["POST"])
def update_settings():
    redir = require_login()
    if redir: return redir
    flash("Settings update not implemented in minimal app.py yet.", "error")
    return redirect(url_for("settings"))

@app.route("/settings/password", methods=["POST"])
def change_password():
    redir = require_login()
    if redir: return redir
    flash("Password change not implemented in minimal app.py yet.", "error")
    return redirect(url_for("settings"))


# =========================
# Local dev entrypoint
# (Render uses: gunicorn app:app --bind 0.0.0.0:$PORT)
# =========================
if __name__ == "__main__":
    app.run(debug=True)
