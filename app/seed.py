# app/seed.py
from datetime import date
from typing import Any, Dict

from sqlalchemy import inspect
from app.models import db, Client, Case, Invoice, Event, Document


# ----------------------
# helpers
# ----------------------

def _has_column(model, name: str) -> bool:
    return name in getattr(model, "__table__", {}).columns.keys()

def _has_relationship(model, name: str) -> bool:
    try:
        rels = inspect(model).relationships
        return name in rels
    except Exception:
        return False

def _wipe_all() -> None:
    """
    Remove demo rows in a dependency-safe order:
    children first, then parents.
    Adjust if your schema differs.
    """
    db.session.query(Document).delete()
    db.session.query(Invoice).delete()
    db.session.query(Event).delete()
    db.session.query(Case).delete()
    db.session.query(Client).delete()
    db.session.commit()


# ----------------------
# inserters
# ----------------------

def _insert_demo() -> None:
    # --- Clients ---
    c1 = Client(name="John Mwangi",  contact="+254712345678", email="john@example.com")
    c2 = Client(name="Mary Atieno",  contact="+254733112233", email="mary@example.com")
    c3 = Client(name="Acme Supplies Ltd", contact="+254701998877", email="info@acme.co.ke")

    db.session.add_all([c1, c2, c3])
    db.session.commit()  # ensure IDs exist

    # Helper to build Case respecting your model shape
    def make_case(client_obj: Client, **base: Dict[str, Any]) -> Case:
        data = dict(base)

        # Prefer FK column if present; otherwise use relationship attr.
        if _has_column(Case, "client_id"):
            data["client_id"] = client_obj.id
        elif _has_relationship(Case, "client"):
            data["client"] = client_obj
        else:
            # Fallback: insert a readable string field if your model has it
            if _has_column(Case, "client_name"):
                data["client_name"] = client_obj.name

        # If your model uses a simple string column for status, this is fine.
        # If you mapped status as a relationship to a Status table, delete the line below
        # and attach the proper Status object here instead.
        data.setdefault("status", "Open")

        return Case(**data)

    # --- Cases ---
    case1 = make_case(
        c1,
        title="CIV 55/2025",
        description="Breach of contract",
        status="Open",
    )
    case2 = make_case(
        c2,
        title="HCC 102/2025",
        description="Land dispute",
        status="Pending",
    )
    db.session.add_all([case1, case2])

    # --- Invoices ---
    # Your Invoice model appears to store a client *name* (string) in `client`.
    inv1 = Invoice(client=c1.name, amount=50000, status="Unpaid", notes="Legal fees advance")
    inv2 = Invoice(client=c2.name, amount=20000, status="Paid",   notes="Filing fee")
    db.session.add_all([inv1, inv2])

    # --- Events ---
    # Use real dates; SQLAlchemy Date columns accept `datetime.date`.
    evt1 = Event(date=date(2025, 9, 1),  type="Court",   description="Court Mention - Case CIV 55/2025")
    evt2 = Event(date=date(2025, 9, 10), type="Meeting", description="Client meeting - Mary Atieno")
    db.session.add_all([evt1, evt2])

    # --- Documents ---
    doc1 = Document(title="Pleading Example", filename="pleading.pdf", notes="Sample pleading")
    doc2 = Document(title="Invoice Sample",  filename="invoice.pdf",  notes="Sample invoice")
    db.session.add_all([doc1, doc2])

    db.session.commit()


# ----------------------
# public API
# ----------------------

def run_seed() -> None:
    """
    Idempotent seed: if any Client exists, do nothing.
    Call this automatically at startup if desired.
    """
    if db.session.query(Client).count() > 0:
        print("Seed skipped: Clients already exist.")
        return
    _insert_demo()
    print("✅ Demo data seeded.")

def run_seed_force() -> None:
    """
    Destructive reset: wipes demo rows then re-inserts.
    Use from Render Shell to refresh the live demo.
    """
    _wipe_all()
    _insert_demo()
    print("✅ Demo data reset and re-seeded.")
