# app/seed.py
from __future__ import annotations

from datetime import date, timedelta

from app import db
from app.models import (
    Client,
    Case,
    Invoice,
    Event,
    Document,
    # ⚠️ If your model is named CaseStatus instead of Status,
    # change the import below to:  from app.models import CaseStatus as Status
    Status,
)


# ---------- helpers ----------

def get_or_create(model, **filters):
    """ORM-safe get or create. Flush so FK ids are available in the same txn."""
    obj = model.query.filter_by(**filters).first()
    if obj:
        return obj
    obj = model(**filters)
    db.session.add(obj)
    db.session.flush()
    return obj


def _wipe_demo_data():
    """
    Remove existing demo rows in correct FK order so the seed is repeatable.
    Adjust filters if you want to keep real data.
    """
    # Child tables first (depend on Case)
    Event.query.delete()      # events depend on case
    Document.query.delete()   # documents depend on case
    Invoice.query.delete()    # invoices may depend on case

    # Cases next
    Case.query.delete()

    # Optionally wipe clients/statuses if you want a truly clean demo
    # (If you have real/production rows you want to keep, filter here instead.)
    Client.query.delete()
    Status.query.delete()

    db.session.flush()


# ---------- main seed payload ----------

def _insert_demo():
    """Create a clean, minimal but realistic demo dataset."""

    # 1) Reference/lookup rows as ORM INSTANCES (not strings)
    #    This is the key fix: Case.status is a RELATIONSHIP → must assign a Status instance.
    status_open = get_or_create(Status, name="OPEN")
    status_closed = get_or_create(Status, name="CLOSED")

    client_dc = get_or_create(
        Client,
        name="Digital Club",
        defaults={}  # ignored by our simple get_or_create; keep for clarity
    )
    # Optional: set/update details if newly created
    if not getattr(client_dc, "phone", None):
        client_dc.phone = "+254 716 202 632"
    if not getattr(client_dc, "email", None):
        client_dc.email = "digitalclub@example.com"

    client_acme = get_or_create(
        Client,
        name="Acme Ltd"
    )
    if not getattr(client_acme, "phone", None):
        client_acme.phone = "+254 700 000 000"
    if not getattr(client_acme, "email", None):
        client_acme.email = "acme@example.com"

    # 2) Cases — assign relationship *instances*
    case1 = Case(
        title="Breach of Contract – Supplier Delay",
        opened_on=date.today(),
        client=client_dc,      # relationship
        status=status_open,    # relationship (✅ FIX: not "OPEN" string)
    )
    case2 = Case(
        title="Debt Recovery – Outstanding Invoice #INV-1042",
        opened_on=date.today() - timedelta(days=10),
        client=client_acme,    # relationship
        status=status_open,    # relationship
    )

    db.session.add_all([case1, case2])
    db.session.flush()  # ensure case ids exist for children

    # 3) Events — attach via relationship
    ev1 = Event(
        case=case1,
        title="Filed plaint at Milimani Commercial",
        kind="FILING",
        event_date=date.today(),
    )
    ev2 = Event(
        case=case1,
        title="Service of Summons – Defendant",
        kind="SERVICE",
        event_date=date.today() + timedelta(days=3),
    )
    ev3 = Event(
        case=case2,
        title="Demand Letter Issued",
        kind="CORRESPONDENCE",
        event_date=date.today() - timedelta(days=9),
    )

    # 4) Documents — attach via relationship
    doc1 = Document(
        case=case1,
        filename="plaint.pdf",
        storage_path="uploads/plaint.pdf",
        doc_type="PLEADING",
    )

    # 5) Invoices — if your Invoice has a relationship to Case, this is fine;
    #    if it uses case_id, swap to case_id=case1.id
    inv1 = Invoice(
        case=case1,
        number="INV-2025-0001",
        amount=15000.00,
        status="UNPAID",  # assuming this is a scalar column on Invoice (OK as string)
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=14),
    )

    db.session.add_all([ev1, ev2, ev3, doc1, inv1])
    db.session.flush()


# ---------- public entry points ----------

def run_seed_safe():
    """
    Insert demo data ONLY if it doesn't already exist.
    Won't wipe — safe for semi-populated DBs.
    """
    try:
        has_any_case = db.session.query(Case.id).first() is not None
        if has_any_case:
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
    """
    Force re-seed: wipes demo data then inserts fresh demo rows.
    Matches how you’ve been calling it from Render shell.
    """
    try:
        _wipe_demo_data()
        _insert_demo()
        db.session.commit()
        print("✅ Seed (force) completed.")
    except Exception as e:
        db.session.rollback()
        print("❌ Seed (force) failed:", e)
        raise
