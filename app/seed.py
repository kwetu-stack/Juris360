# app/seed.py
from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy.inspection import inspect as sa_inspect

from app import db
from app.models import Client, Case, Invoice, Event, Document, CaseStatus as Status


# ---------- helpers ----------

def get_or_create(model, **filters):
    obj = model.query.filter_by(**filters).first()
    if obj:
        return obj
    obj = model(**filters)
    db.session.add(obj)
    db.session.flush()
    return obj


def _get_or_create_status(label: str):
    """
    Create/find a status row on CaseStatus using a best-effort string field.
    Common field names tried in order: name/code/label/value/title/status.
    """
    for field in ("name", "code", "label", "value", "title", "status"):
        if hasattr(Status, field):
            filt = {field: label}
            obj = Status.query.filter_by(**filt).first()
            if obj:
                return obj
            obj = Status(**filt)
            db.session.add(obj)
            db.session.flush()
            return obj
    raise RuntimeError(
        f"Could not find a string field on {Status.__name__} "
        f"(tried name/code/label/value/title/status)."
    )


def set_first_attr(obj, names: tuple[str, ...], value):
    """Set the first attribute that exists on obj from names; return the name or None."""
    for n in names:
        if hasattr(obj, n):
            setattr(obj, n, value)
            return n
    return None


def _wipe_demo_data():
    """Make the seed repeatable by cleaning tables in FK order."""
    # Children first (depend on Case)
    Event.query.delete()
    Document.query.delete()
    Invoice.query.delete()
    # Parents
    Case.query.delete()
    Client.query.delete()
    # Keep CaseStatus rows (reusable)
    db.session.flush()


# ---------- main seed payload ----------

def _insert_demo():
    """Create a clean, minimal, schema-accurate demo dataset."""
    # Clients
    client_dc = get_or_create(Client, name="Digital Club")
    if not getattr(client_dc, "phone", None):
        client_dc.phone = "+254 716 202 632"
    if not getattr(client_dc, "email", None):
        client_dc.email = "digitalclub@example.com"

    client_acme = get_or_create(Client, name="Acme Ltd")
    if not getattr(client_acme, "phone", None):
        client_acme.phone = "+254 700 000 000"
    if not getattr(client_acme, "email", None):
        client_acme.email = "acme@example.com"

    # Case statuses (relationship instances)
    status_open = _get_or_create_status("OPEN")
    # status_closed = _get_or_create_status("CLOSED")  # available if needed

    now = datetime.utcnow()

    # Cases — use created_at/updated_at (as per your schema)
    case1 = Case(
        title="Breach of Contract – Supplier Delay",
        client=client_dc,
        status=status_open,
        created_at=now,
        updated_at=now,
    )
    case2 = Case(
        title="Debt Recovery – Outstanding Invoice #INV-1042",
        client=client_acme,
        status=status_open,
        created_at=now - timedelta(days=10),
        updated_at=now - timedelta(days=10),
    )

    db.session.add_all([case1, case2])
    db.session.flush()

    # Events — attach by relationship, detect date-like field name
    ev1 = Event(case=case1, title="Filed plaint at Milimani Commercial")
    set_first_attr(ev1, ("kind", "type", "category", "label"), "FILING")
    set_first_attr(ev1, ("event_date", "date", "on", "scheduled_for", "due_on", "due_date"), now)

    ev2 = Event(case=case1, title="Service of Summons – Defendant")
    set_first_attr(ev2, ("kind", "type", "category", "label"), "SERVICE")
    set_first_attr(ev2, ("event_date", "date", "on", "scheduled_for", "due_on", "due_date"), now + timedelta(days=3))

    ev3 = Event(case=case2, title="Demand Letter Issued")
    set_first_attr(ev3, ("kind", "type", "category", "label"), "CORRESPONDENCE")
    set_first_attr(ev3, ("event_date", "date", "on", "scheduled_for", "due_on", "due_date"), now - timedelta(days=9))

    # Documents — attach by relationship
    doc1 = Document(
        case=case1,
        filename="plaint.pdf",
        storage_path="uploads/plaint.pdf",
    )
    set_first_attr(doc1, ("doc_type", "type", "kind", "category", "label"), "PLEADING")

    # Invoices — attach by relationship; detect issue/due date fields
    inv1 = Invoice(
        case=case1,  # if your model uses FK instead, use case_id=case1.id
        number="INV-2025-0001",
        amount=15000.00,
        status="UNPAID",  # assuming scalar column on Invoice
    )
    set_first_attr(inv1, ("issue_date", "issued_on", "date", "created_at", "created_on"), now)
    set_first_attr(inv1, ("due_date", "due_on", "deadline"), now + timedelta(days=14))

    db.session.add_all([ev1, ev2, ev3, doc1, inv1])
    db.session.flush()


# ---------- public entry points ----------

def run_seed_safe():
    """Insert demo data only if there are no cases yet."""
    try:
        if db.session.query(Case.id).first() is not None:
            print("ℹ️ Seed skipped: cases already exist.")
            return
        _insert_demo()
        db.session.commit()
        print("✅ Seed (safe) completed.")
    except Exception as e:
        db.session.rollback()
        print("❌ Seed (safe) failed:", e)
        raise


def run_seed_force():
    """Force re-seed by wiping demo data first."""
    try:
        _wipe_demo_data()
        _insert_demo()
        db.session.commit()
        print("✅ Seed (force) completed.")
    except Exception as e:
        db.session.rollback()
        print("❌ Seed (force) failed:", e)
        raise
