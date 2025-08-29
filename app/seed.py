# app/seed.py
from __future__ import annotations

from datetime import date, timedelta
from sqlalchemy.inspection import inspect as sa_inspect

from app import db
from app.models import Client, Case, Invoice, Event, Document


# ---------- helpers ----------

def get_or_create(model, **filters):
    obj = model.query.filter_by(**filters).first()
    if obj:
        return obj
    obj = model(**filters)
    db.session.add(obj)
    db.session.flush()
    return obj

def _status_model():
    """Discover Case.status related model regardless of actual class name."""
    rel = sa_inspect(Case).relationships.get("status")
    if not rel:
        raise RuntimeError("Case.status relationship not found. Check your models.")
    return rel.mapper.class_

def _get_or_create_status(label: str):
    """Create/find a status row using a best-effort string field name."""
    StatusModel = _status_model()
    for field in ("name", "code", "label", "value", "title", "status"):
        if hasattr(StatusModel, field):
            filt = {field: label}
            obj = StatusModel.query.filter_by(**filt).first()
            if obj:
                return obj
            obj = StatusModel(**filt)
            db.session.add(obj)
            db.session.flush()
            return obj
    raise RuntimeError(
        f"Could not find a string field on {StatusModel.__name__} "
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
    Event.query.delete()
    Document.query.delete()
    Invoice.query.delete()
    Case.query.delete()
    Client.query.delete()
    # Keep status rows; they’re reusable.
    db.session.flush()


# ---------- main seed payload ----------

def _insert_demo():
    """Create a clean, minimal but realistic demo dataset."""
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

    # Status (relationship instance)
    status_open = _get_or_create_status("OPEN")

    # Cases — set whichever date field exists
    case1 = Case(
        title="Breach of Contract – Supplier Delay",
        client=client_dc,
        status=status_open,
    )
    set_first_attr(
        case1,
        ("opened_on", "opened_at", "filed_on", "date_opened", "created_on", "created_at", "start_date", "date"),
        date.today(),
    )

    case2 = Case(
        title="Debt Recovery – Outstanding Invoice #INV-1042",
        client=client_acme,
        status=status_open,
    )
    set_first_attr(
        case2,
        ("opened_on", "opened_at", "filed_on", "date_opened", "created_on", "created_at", "start_date", "date"),
        date.today() - timedelta(days=10),
    )

    db.session.add_all([case1, case2])
    db.session.flush()

    # Events — set case + whichever date field exists
    ev1 = Event(case=case1, title="Filed plaint at Milimani Commercial", kind="FILING")
    set_first_attr(ev1, ("event_date", "date", "on", "scheduled_for", "due_on", "due_date"), date.today())

    ev2 = Event(case=case1, title="Service of Summons – Defendant", kind="SERVICE")
    set_first_attr(ev2, ("event_date", "date", "on", "scheduled_for", "due_on", "due_date"), date.today() + timedelta(days=3))

    ev3 = Event(case=case2, title="Demand Letter Issued", kind="CORRESPONDENCE")
    set_first_attr(ev3, ("event_date", "date", "on", "scheduled_for", "due_on", "due_date"), date.today() - timedelta(days=9))

    # Documents
    doc1 = Document(
        case=case1,
        filename="plaint.pdf",
        storage_path="uploads/plaint.pdf",
    )
    # If your Document has a type/name field:
    set_first_attr(doc1, ("doc_type", "type", "kind", "category", "label"), "PLEADING")

    # Invoice — attach to case; set dates via detection
    inv1 = Invoice(
        case=case1,  # use case_id=case1.id if your model uses FK field instead of relationship
        number="INV-2025-0001",
        amount=15000.00,
        status="UNPAID",  # assuming scalar column on Invoice
    )
    set_first_attr(inv1, ("issue_date", "issued_on", "date", "created_at", "created_on"), date.today())
    set_first_attr(inv1, ("due_date", "due_on", "deadline"), date.today() + timedelta(days=14))

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
