# app/seed.py
from datetime import date
from app.models import db, Client, Case, Invoice, Event, Document

def _get_or_create_client(name, contact, email):
    c = Client.query.filter_by(name=name).first()
    if not c:
        c = Client(name=name, contact=contact, email=email)
        db.session.add(c)
        db.session.commit()
    return c

def _get_or_create_case(title, description, status, client_id):
    c = Case.query.filter_by(title=title).first()
    if not c:
        c = Case(title=title, description=description, status=status, client_id=client_id)
        db.session.add(c)
        db.session.commit()
    return c

def _ensure_invoice(client_id, amount, status, notes):
    exists = Invoice.query.filter_by(client_id=client_id, amount=amount, status=status, notes=notes).first()
    if not exists:
        db.session.add(Invoice(client_id=client_id, amount=amount, status=status, notes=notes))

def _ensure_event(d, description, type_):
    exists = Event.query.filter_by(date=d, description=description, type=type_).first()
    if not exists:
        db.session.add(Event(date=d, description=description, type=type_))

def _ensure_document(title, filename, case_id=None, notes=None):
    exists = Document.query.filter_by(title=title, filename=filename).first()
    if not exists:
        db.session.add(Document(title=title, filename=filename, case_id=case_id, notes=notes))

def run_seed_force():
    """
    Idempotent seed: creates missing demo rows; safe to run many times.
    Use this on Render to recover from a partial seed.
    """
    try:
        # --- Clients ---
        john = _get_or_create_client("John Mwangi", "+254712345678", "john@example.com")
        mary = _get_or_create_client("Mary Atieno", "+254733112233", "mary@example.com")
        acme = _get_or_create_client("Acme Supplies Ltd", "+254701998877", "info@acme.co.ke")

        # --- Cases ---
        civ55 = _get_or_create_case("CIV 55/2025", "Breach of contract", "Open", john.id)
        hcc102 = _get_or_create_case("HCC 102/2025", "Land dispute", "Pending", mary.id)

        # --- Invoices (use client_id, not a string) ---
        _ensure_invoice(john.id, 50000, "Unpaid", "Legal fees advance")
        _ensure_invoice(mary.id, 20000, "Paid", "Filing fee")

        # --- Events (use real dates) ---
        _ensure_event(date(2025, 9, 1), "Court Mention - Case CIV 55/2025", "Court")
        _ensure_event(date(2025, 9, 10), "Client meeting - Mary Atieno", "Meeting")

        # --- Documents (case links optional) ---
        _ensure_document("Pleading Example", "pleading.pdf", case_id=civ55.id, notes="Sample pleading")
        _ensure_document("Invoice Sample", "invoice.pdf", case_id=None, notes="Sample PDF")

        db.session.commit()
        print("✅ Demo data present (created missing rows).")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Seed error: {e}")

def run_seed():
    """
    Original behavior: do nothing if any clients already exist.
    Kept for completeness; we’ll use run_seed_force() instead.
    """
    if Client.query.count() > 0:
        print("Seed skipped: Clients already exist.")
        return
    run_seed_force()
