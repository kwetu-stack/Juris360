# app/seed.py
from datetime import date
from typing import Dict, Any, List

from app.models import db, Client, Case, Invoice, Event, Document


# -------- helpers --------

def _iso(d: date) -> str:
    return d.isoformat()


def _cols(model) -> set:
    """Return actual scalar column names for a model (excludes relationships)."""
    return {c.name for c in model.__table__.columns}  # type: ignore[attr-defined]


def _wipe_all():
    """Delete in a dependency-safe order (children -> parents)."""
    db.session.query(Document).delete()
    db.session.query(Invoice).delete()
    db.session.query(Case).delete()
    db.session.query(Event).delete()
    db.session.query(Client).delete()
    db.session.commit()


def _safe_create(model, data: Dict[str, Any]):
    """
    Create a row using only the model's scalar columns to avoid passing
    relationship objects/unknown fields that trigger SA errors.
    """
    cols = _cols(model)
    clean = {k: v for k, v in data.items() if k in cols}
    obj = model(**clean)
    db.session.add(obj)
    return obj


def _insert_demo():
    """Insert a small, coherent demo dataset with safe column detection."""
    # --- Clients ---
    c1 = _safe_create(Client, dict(
        name="John Mwangi", contact="+254712345678", email="john@example.com"
    ))
    c2 = _safe_create(Client, dict(
        name="Mary Atieno", contact="+254733112233", email="mary@example.com"
    ))
    c3 = _safe_create(Client, dict(
        name="Acme Supplies Ltd", contact="+254701998877", email="info@acme.co.ke"
    ))
    db.session.flush()  # ensure IDs

    # Decide how to link cases -> clients
    case_cols = _cols(Case)
    case_link_field = None
    if "client_id" in case_cols:
        case_link_field = "client_id"
    elif "client" in case_cols:
        # Some schemas store the client's *name* as a scalar column
        case_link_field = "client"

    cases_payload: List[Dict[str, Any]] = [
        dict(title="CIV 55/2025", description="Breach of contract", status="Open"),
        dict(title="HCC 102/2025", description="Land dispute", status="Pending"),
    ]

    # Add linking if the column exists (ID or name)
    if case_link_field == "client_id":
        cases_payload[0][case_link_field] = c1.id
        cases_payload[1][case_link_field] = c2.id
    elif case_link_field == "client":
        cases_payload[0][case_link_field] = c1.name
        cases_payload[1][case_link_field] = c2.name
    # else: no link field—insert without linkage

    case1 = _safe_create(Case, cases_payload[0])
    case2 = _safe_create(Case, cases_payload[1])

    # --- Invoices ---
    # Many lightweight schemas store client as a plain string column; others use client_id
    inv_cols = _cols(Invoice)
    if "client_id" in inv_cols:
        inv1 = _safe_create(Invoice, dict(client_id=c1.id, amount=50000, status="Unpaid", notes="Legal fees advance"))
        inv2 = _safe_create(Invoice, dict(client_id=c2.id, amount=20000, status="Paid", notes="Filing fee"))
    elif "client" in inv_cols:
        inv1 = _safe_create(Invoice, dict(client=c1.name, amount=50000, status="Unpaid", notes="Legal fees advance"))
        inv2 = _safe_create(Invoice, dict(client=c2.name, amount=20000, status="Paid", notes="Filing fee"))
    else:
        # Fall back to minimal columns if neither exists
        inv1 = _safe_create(Invoice, dict(amount=50000, status="Unpaid", notes="Legal fees advance"))
        inv2 = _safe_create(Invoice, dict(amount=20000, status="Paid", notes="Filing fee"))

    # --- Events ---
    _safe_create(Event, dict(date=_iso(date(2025, 9, 1)), type="Court",   description="Court Mention - Case CIV 55/2025")))
    _safe_create(Event, dict(date=_iso(date(2025, 9, 10)), type="Meeting", description="Client meeting - Mary Atieno"))

    # --- Documents ---
    _safe_create(Document, dict(title="Pleading Example", filename="pleading.pdf", notes="Sample pleading"))
    _safe_create(Document, dict(title="Invoice Sample",  filename="invoice.pdf",  notes="Sample invoice"))

    db.session.commit()


# -------- public API --------

def run_seed():
    """Non-destructive: skip if any Client exists."""
    if db.session.query(Client).count() > 0:
        print("Seed skipped: Clients already exist.")
        return
    _insert_demo()
    print("✅ Demo data seeded.")


def run_seed_force():
    """Destructive reset: wipe and re-seed. Use this from Render shell."""
    _wipe_all()
    _insert_demo()
    print("✅ Demo data reset and re-seeded.")
