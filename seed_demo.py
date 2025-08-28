# seed_demo.py — populate dropdowns + Kenyan demo data
import os, sqlite3, datetime, base64, pathlib

DB = os.path.abspath("data/juris360.db")
UP = os.path.abspath("data/uploads")
pathlib.Path("data").mkdir(parents=True, exist_ok=True)
pathlib.Path(UP).mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB)
cur = conn.cursor()

# create tables (matches app/models.py)
cur.executescript("""
CREATE TABLE IF NOT EXISTS user (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT);
CREATE TABLE IF NOT EXISTS case_status (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS doc_type (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS billing_status (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS event_type (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);

CREATE TABLE IF NOT EXISTS client (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, contact TEXT, email TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS "case" (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, title TEXT, description TEXT, status_id INTEGER, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS document (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, case_ref TEXT, type_id INTEGER, notes TEXT, uploaded_at TEXT, size_bytes INTEGER);
CREATE TABLE IF NOT EXISTS invoice (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, amount REAL, status_id INTEGER, issued_on TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS event (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, description TEXT, type_id INTEGER);
""")

# ensure admin exists
cur.execute("INSERT OR IGNORE INTO user (username,password) VALUES (?,?)", ("admin","kwetutech00"))

# dropdowns
for n in ["Open","Pending","Closed"]:
    cur.execute("INSERT OR IGNORE INTO case_status (name) VALUES (?)", (n,))
for n in ["Affidavit","Pleading","Bundle","Exhibit","Invoice","Other"]:
    cur.execute("INSERT OR IGNORE INTO doc_type (name) VALUES (?)", (n,))
for n in ["Unpaid","Partial","Paid","Disputed"]:
    cur.execute("INSERT OR IGNORE INTO billing_status (name) VALUES (?)", (n,))
for n in ["Hearing","Filing","Meeting","Deadline","Other"]:
    cur.execute("INSERT OR IGNORE INTO event_type (name) VALUES (?)", (n,))

# map ids
cur.execute("SELECT id,name FROM case_status"); cs = {n:i for i,n in cur.fetchall()}
cur.execute("SELECT id,name FROM doc_type"); dt = {n:i for i,n in cur.fetchall()}
cur.execute("SELECT id,name FROM billing_status"); bs = {n:i for i,n in cur.fetchall()}
cur.execute("SELECT id,name FROM event_type"); et = {n:i for i,n in cur.fetchall()}

# clients
now = datetime.datetime.utcnow().isoformat(timespec="seconds")
clients = [
    ("Mumbi & Co. Advocates","0712 345 678","info@mumbiadvocates.co.ke"),
    ("Kariuki Enterprises Ltd","0722 987 654","accounts@kariuki.co.ke"),
    ("Achieng Logistics","0733 555 111","ops@achienglogistics.com"),
    ("Wanjiku Hardware","0700 112 233","sales@wanjikuhardware.co.ke"),
    ("Nyaga & Sons","0799 888 777","nyaga@nyagaandsons.co.ke"),
    ("Makena Designs","0711 321 321","hello@makenadesigns.co.ke"),
    ("Mutua Dairy","0701 454 545","admin@mutuadairy.co.ke"),
    ("Ochieng & Ouma LLP","0740 987 321","admin@oollp.co.ke"),
    ("Njeri Estates","0790 222 333","office@njeri-estates.co.ke"),
    ("Kwamboka Foods","0755 666 777","orders@kwambokafoods.co.ke"),
]
for c in clients:
    cur.execute("INSERT INTO client (name,contact,email,created_at,updated_at) VALUES (?,?,?,?,?)", (*c, now, now))

cur.execute("SELECT id FROM client ORDER BY id")
C = [r[0] for r in cur.fetchall()]

# cases
cases = [
    (C[1], "Republic v. Kariuki – CR 45/2024", "Criminal matter at Milimani Law Courts", cs["Open"]),
    (C[2], "Achieng Logistics v. KRA – HCCC 102/2025", "Tax dispute", cs["Pending"]),
    (C[0], "Mumbi & Co. v. Tenant – CMCC 12/2025", "Landlord-tenant dispute", cs["Closed"]),
    (C[3], "Wanjiku Hardware v. County Govt – JR 18/2024", "Judicial review", cs["Open"]),
    (C[4], "Nyaga & Sons v. NEMA – ELC 77/2025", "Environmental compliance", cs["Open"]),
    (C[5], "Makena Designs v. Supplier – CMCC 201/2025", "Breach of contract", cs["Pending"]),
    (C[6], "Mutua Dairy v. KEBS – HCCC 78/2024", "Standards dispute", cs["Closed"]),
    (C[7], "Ochieng & Ouma LLP v. Former Partner – HCCC 3/2025", "Partnership wrangle", cs["Open"]),
    (C[8], "Njeri Estates v. Trespassers – ELC 56/2024", "Land trespass", cs["Pending"]),
    (C[9], "Kwamboka Foods v. Transporter – CMCC 90/2025", "Damaged goods claim", cs["Open"]),
    (C[0], "Republic v. Unknown – CR 99/2025", "Criminal investigation", cs["Open"]),
    (C[1], "Kariuki Enterprises v. City Council – JR 21/2025", "Rates review", cs["Pending"]),
]
for row in cases:
    cur.execute("INSERT INTO 'case' (client_id,title,description,status_id,created_at,updated_at) VALUES (?,?,?,?,?,?)", (*row, now, now))

# sample files (tiny)
png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7lD6sAAAAASUVORK5CYII=")
open(os.path.join(UP,"stamp.png"),"wb").write(png)
open(os.path.join(UP,"notice.txt"),"w",encoding="utf-8").write("Sample notice for Juris360.")
pdf = b"%PDF-1.1\\n% tiny placeholder\\n"
open(os.path.join(UP,"pleading.pdf"),"wb").write(pdf)

# documents
docs = [
    ("pleading.pdf", "HCCC 102/2025", dt["Pleading"], "Statement of Claim"),
    ("stamp.png", "CMCC 201/2025", dt["Exhibit"], "Stamped receipt"),
    ("notice.txt", "ELC 77/2025", dt["Other"], "Notice to comply"),
    ("pleading.pdf", "CR 45/2024", dt["Pleading"], "Charge sheet"),
    ("stamp.png", "JR 18/2024", dt["Exhibit"], "Court stamp"),
    ("notice.txt", "CMCC 12/2025", dt["Other"], "Notice to show cause"),
]
for fname, case_ref, type_id, notes in docs:
    size = os.path.getsize(os.path.join(UP, fname))
    cur.execute("INSERT INTO document (filename,case_ref,type_id,notes,uploaded_at,size_bytes) VALUES (?,?,?,?,?,?)",
                (fname, case_ref, type_id, notes, now, size))

# invoices
invoices = [
    (C[0], 150000.00, bs["Unpaid"], "Instruction fee – CMCC 12/2025"),
    (C[2], 320000.00, bs["Partial"], "Filing & hearing fees – HCCC 102/2025"),
    (C[3], 58000.00,  bs["Paid"],    "Advisory retainer – Q2"),
    (C[5], 94000.00,  bs["Disputed"],"Consultation & drafting"),
    (C[7], 210000.00, bs["Unpaid"],  "Partnership dispute – HCCC 3/2025"),
    (C[9], 76000.00,  bs["Paid"],    "Demand letter & negotiations"),
]
for clid, amount, status_id, notes in invoices:
    cur.execute("INSERT INTO invoice (client_id,amount,status_id,issued_on,notes) VALUES (?,?,?,?,?)",
                (clid, amount, status_id, now[:10], notes))

# events
events = [
    ("2025-09-05", "Hearing at Milimani for CR 45/2024", et["Hearing"]),
    ("2025-09-12", "File submissions in HCCC 102/2025",    et["Filing"]),
    ("2025-09-15", "Client meeting: Achieng Logistics",     et["Meeting"]),
    ("2025-10-01", "Deadline: Witness statements ELC 77/2025", et["Deadline"]),
    ("2025-08-25", "Mention for CMCC 201/2025",             et["Hearing"]),
    ("2025-09-20", "Negotiation session – partnership wrangle", et["Meeting"]),
]
for d, desc, t in events:
    cur.execute("INSERT INTO event (date,description,type_id) VALUES (?,?,?)", (d, desc, t))

conn.commit(); conn.close()
print("Seed complete.")
