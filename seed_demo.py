import sqlite3, datetime

DB="juris360.db"
conn=sqlite3.connect(DB)
cur=conn.cursor()

# ---- Clients
cur.executemany("""
INSERT INTO clients (name, contact, email)
VALUES (?, ?, ?)
""", [
    ("Wanjiru Estates Ltd", "+254 712 000 111", "legal@wanjiruestates.co.ke"),
    ("John Ngugi", "+254 723 555 987", "john.ngugi@email.com"),
    ("Amina Hassan", "+254 733 444 222", "amina.hassan@email.com"),
])

# ---- Cases
cur.executemany("""
INSERT INTO cases (title, client, status)
VALUES (?, ?, ?)
""", [
    ("CIV 55/23 – Ngugi v. Amani", "Wanjiru Estates Ltd", "Open"),
    ("CR 1029/24 – People v. Karanja", "Republic", "Pending"),
    ("AP 19/25 – Amina v. Wanjiru Estates", "Amina Hassan", "Closed"),
])

# ---- Schedule
today = datetime.date.today()
cur.executemany("""
INSERT INTO schedule (date, description, type)
VALUES (?, ?, ?)
""", [
    ((today + datetime.timedelta(days=2)).isoformat(), "CR 1029/24 Hearing (Milimani)", "Hearing"),
    ((today + datetime.timedelta(days=3)).isoformat(), "Client Consult – Oketch & Co.", "Meeting"),
    ((today + datetime.timedelta(days=1)).isoformat(), "Draft Defence – CIV 88/25", "Task"),
])

# ---- Billing
cur.executemany("""
INSERT INTO billing (client, amount, status)
VALUES (?, ?, ?)
""", [
    ("Wanjiru Estates Ltd", 120000, "Unpaid"),
    ("John Ngugi", 45000, "Partially Paid"),
    ("Amina Hassan", 210000, "Paid"),
])

# ---- Documents (placeholder rows)
cur.executemany("""
INSERT INTO documents (title, filename)
VALUES (?, ?)
""", [
    ("Affidavit – CIV 55/23", "affidavit_civ55_23.pdf"),
    ("Pleadings – AP 19/25", "pleadings_ap19_25.pdf"),
])

conn.commit()
conn.close()
print("Seed data inserted.")
