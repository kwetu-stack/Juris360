from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, os

app = Flask(__name__)
app.secret_key = "juris360_secret"

DB_NAME = "juris360.db"

# ===== Database Init =====
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        # Users table
        cur.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )""")
        # Cases (simple schema)
        cur.execute("""CREATE TABLE IF NOT EXISTS cases(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            client TEXT,
            status TEXT
        )""")
        # Clients (simple schema)
        cur.execute("""CREATE TABLE IF NOT EXISTS clients(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contact TEXT,
            email TEXT
        )""")
        # Schedule (demo)
        cur.execute("""CREATE TABLE IF NOT EXISTS schedule(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            description TEXT,
            type TEXT
        )""")
        # Billing (demo)
        cur.execute("""CREATE TABLE IF NOT EXISTS billing(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT,
            amount REAL,
            status TEXT
        )""")
        # Documents (demo)
        cur.execute("""CREATE TABLE IF NOT EXISTS documents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            filename TEXT
        )""")
        conn.commit()
    seed_admin()

# ===== Seed default admin =====
def seed_admin():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username=?", ("admin",))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (username, password) VALUES (?,?)", ("admin", "admin"))
            conn.commit()

# ===== Helpers =====
def is_logged_in():
    return "username" in session

def require_login():
    if not is_logged_in():
        return redirect(url_for("login"))
    return None

# ===== Home / Auth =====
@app.route("/")
def home():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username=? AND password=?", (username, password))
            if cur.fetchone():
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

# ===== Pages =====
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

    # Allow POST from the modal in billing.html (store a minimal record)
    if request.method == "POST":
        client_name = request.form.get("client_name", "").strip()
        amount = request.form.get("amount", "").strip()
        status = request.form.get("status", "Unpaid").strip() or "Unpaid"
        try:
            amount_val = float(amount or 0)
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

# ===== NEW: Add Case (matches add-case.html) =====
@app.route("/add-case", methods=["GET", "POST"])
def add_case():
    redir = require_login()
    if redir: return redir

    if request.method == "POST":
        # Map the rich form to the simple table:
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

# ===== NEW: Add Client (matches add-client.html) =====
@app.route("/add-client", methods=["GET", "POST"])
def add_client():
    redir = require_login()
    if redir: return redir

    if request.method == "POST":
        # Map the rich form to the simple table:
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

# ===== Stubs so template links don’t 404 (you can wire later) =====
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

# ===== Run App =====
if __name__ == "__main__":
    if not os.path.exists(DB_NAME):
        init_db()
    else:
        # Ensure admin exists even if DB pre-existed
        seed_admin()
    app.run(debug=True)
