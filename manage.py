# manage.py  — Temporary DB reset page (DELETE after use)
import os
import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for, flash

# ---- Config ----
DATA_DIR   = os.environ.get("DATA_DIR", ".")
DB_NAME    = os.path.join(DATA_DIR, "juris360.db")
# Require a token to access the reset page (set this in Render → Environment)
RESET_TOKEN = os.environ.get("RESET_TOKEN", "set-a-strong-temp-token")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "temp-secret-for-reset")

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Juris360 · Admin Reset</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; background:#0b1324; color:#e6edf3; display:flex; align-items:center; justify-content:center; height:100vh; }
    .card { width: 420px; background:#121a2b; padding:24px; border-radius:14px; box-shadow: 0 8px 30px rgba(0,0,0,.4); }
    h2 { margin-top:0; }
    label { display:block; margin:12px 0 6px; font-size:14px; color:#b7c3d0; }
    input, button, select { width:100%; padding:10px 12px; border-radius:10px; border:1px solid #273149; background:#0e1730; color:#e6edf3; }
    button { margin-top:14px; background:#1f6feb; border:none; cursor:pointer; }
    .warn { background:#332108; color:#ffd277; padding:10px 12px; border-radius:10px; margin-bottom:14px; font-size:14px; }
    .muted { color:#9fb1c1; font-size:12px; margin-top:10px; }
    .ok { color:#7ef0a5; font-size:14px; margin-top:8px; }
    .err { color:#ff8a8a; font-size:14px; margin-top:8px; }
    details { margin-top:12px; }
    code { background:#0e1730; padding:2px 6px; border-radius:6px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="warn"><b>Temporary Tool:</b> remove <code>manage.py</code> after use.</div>
    <h2>Reset Admin Password</h2>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for cat, msg in messages %}
          <div class="{{ 'ok' if cat=='success' else 'err' }}">{{ msg }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <form method="post" action="{{ url_for('reset') }}">
      <label>Access Token</label>
      <input name="token" placeholder="RESET_TOKEN" required>

      <label>Username</label>
      <input name="username" value="admin" required>

      <label>New Password</label>
      <input name="password" type="password" placeholder="e.g. kwetutech00" required>

      <button type="submit">Update Password</button>
      <div class="muted">DB path: <code>{{ db_path }}</code></div>
    </form>

    <details>
      <summary style="cursor:pointer;margin-top:12px;">Show current users</summary>
      <div class="muted">
        {% if users %}
          <ul>
            {% for u in users %}
              <li>#{{u[0]}} — {{u[1]}} (password set)</li>
            {% endfor %}
          </ul>
        {% else %}
          <em>No users found.</em>
        {% endif %}
      </div>
    </details>
  </div>
</body>
</html>
"""

def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    return sqlite3.connect(DB_NAME)

def fetch_users():
    con = _conn()
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )""")
    con.commit()
    cur.execute("SELECT id, username FROM users ORDER BY id ASC")
    rows = cur.fetchall()
    con.close()
    # Don’t ever expose hashed/plain passwords here.
    return [(r[0], r[1]) for r in rows]

@app.get("/")
def form():
    return render_template_string(TEMPLATE, db_path=DB_NAME, users=fetch_users())

@app.post("/reset")
def reset():
    token = request.form.get("token","").strip()
    if token != RESET_TOKEN:
        flash("Invalid reset token.", "error")
        return redirect(url_for("form"))

    username = (request.form.get("username") or "admin").strip()
    new_pass = (request.form.get("password") or "").strip()
    if not new_pass:
        flash("Password is required.", "error")
        return redirect(url_for("form"))

    con = _conn()
    cur = con.cursor()
    cur.execute("""
    INSERT INTO users (username, password)
    VALUES (?, ?)
    ON CONFLICT(username) DO UPDATE SET password=excluded.password
    """, (username, new_pass))
    con.commit()
    con.close()
    flash(f"Password updated for '{username}'.", "success")
    return redirect(url_for("form"))

if __name__ == "__main__":
    # Local run only. On Render, set Start Command temporarily to:  python manage.py
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
