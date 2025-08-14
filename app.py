import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename

# =========================
# Config (env-driven)
# =========================
DATA_DIR = os.environ.get("DATA_DIR", ".")  # e.g., /var/data on Render disk
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
    conn = get_db()
    cur = conn.cursor()

    # Example tables (adjust as per your system)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT
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

    conn.commit()
    conn.close()

# =========================
# Routes
# =========================
@app.route("/")
def index():
    if "user" in session:
        return render_template("dashboard.html", user=session["user"])
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")
        if user == ADMIN_USER and pw == ADMIN_PASS:
            session["user"] = user
            flash("Login successful!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# Clients
@app.route("/clients")
def view_clients():
    conn = get_db()
    clients = conn.execute("SELECT * FROM clients").fetchall()
    conn.close()
    return render_template("view-clients.html", clients=clients)

@app.route("/clients/add", methods=["POST"])
def add_client():
    name = request.form.get("name")
    contact = request.form.get("contact")
    conn = get_db()
    conn.execute("INSERT INTO clients (name, contact) VALUES (?, ?)", (name, contact))
    conn.commit()
    conn.close()
    flash("Client added successfully!", "success")
    return redirect(url_for("view_clients"))

# Cases
@app.route("/cases")
def view_cases():
    conn = get_db()
    cases = conn.execute("""
        SELECT cases.*, clients.name as client_name
        FROM cases
        LEFT JOIN clients ON cases.client_id = clients.id
    """).fetchall()
    conn.close()
    return render_template("view-cases.html", cases=cases)

@app.route("/cases/add", methods=["POST"])
def add_case():
    client_id = request.form.get("client_id")
    title = request.form.get("title")
    description = request.form.get("description")
    status = request.form.get("status", "Open")
    conn = get_db()
    conn.execute("INSERT INTO cases (client_id, title, description, status) VALUES (?, ?, ?, ?)",
                 (client_id, title, description, status))
    conn.commit()
    conn.close()
    flash("Case added successfully!", "success")
    return redirect(url_for("view_cases"))

# =========================
# Main
# =========================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
