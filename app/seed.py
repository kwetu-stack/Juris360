# app/seed.py

from datetime import date
from app.models import db, Client, Case, Invoice, Event, Document


# ------------ helpers ------------

def _iso(d: date) -> str:
    """Return ISO date string (YYYY-MM-DD)."""
    return d.isoformat()


def _wipe_all():
    """
    Remove existing demo rows in a dependency-safe order.
    Adjust order if your models have different FKs.
    """
    # Children -> parents
    db.session.query(Document).delete()
    db.session.query(Invoice).delete()
    db.session.query(Case).delete()
    db.session.query(Event).delete()
    db.session.query(Client).delete()
    db.session.commit()


def _insert_demo():
    """Insert a small, coherent demo dataset."""
    # --- Clients ---
    c1 = Client(name="John Mwangi",  contact="+254712345678", email="john@example.com")
    c2 = Client(name="Mary Atieno",  contact="+254733112233", email="mary@example.com")
    c3 = Client(name="Acme Supplies Ltd", contact="+254701998877", email="info@acme.co.ke")

    db.session.add_all([c1, c2, c3])
    db.session.commit()  # ensure IDs for FK use below

    # --- Cases ---
    case1 = Case(
        title="CIV 55/2025",
        description="Breach of contract",
        status="Open",
        client_id=c1.id,
    )
    case2 = Case(
        title="HCC 102/2025",
        description="Land dispute",
        status="Pending",
        client_id=c2.id,
    )
    db.session.add_all([case1, case2])

    # --- Invoices ---
    # (Assuming your Invoice model stores the client's name as a string field `client`)
    inv1 = Invoice(client=c1.name, amount=50000, status="Unpaid", notes="Legal fees advance")
    inv2 = Invoice(client=c2.name, amount=20000, status="Paid",   notes="Filing fee")
    db.session.add_all([inv1, inv2])

    # --- Events ---
    evt1 = Event(date=_iso(date(2025, 9, 1)),  type="Court",   description="Court Mention - Case CIV 55/2025")
    evt2 = Event(date=_iso(date(2025, 9, 10)), type="Meeting", description="Client meeting - Mary Atieno")
    db.session.add_all([evt1, evt2])

    # --- Documents ---
    # (Assuming minimal fields: title, filename, optional notes)
    doc1 = Document(title="Pleading Example", filename="pleading.pdf", notes="Sample pleading")
    doc2 = Document(title="Invoice Sample",  filename="invoice.pdf",  notes="Sample invoice")
    db.session.add_all([doc1, doc2])

    db.session.commit()


# ------------ public API ------------

def run_seed():
    """
    Safe seeding: if any Client exists, we assume the DB already has data
    and do nothing. Call this automatically at startup if desired.
    """
    if db.session.query(Client).count() > 0:
        print("Seed skipped: Clients already exist.")
        return
    _insert_demo()
    print("✅ Demo data seeded.")


def run_seed_force():
    """
    Destructive reset: wipe demo rows and re-insert.
    Use from Render shell when you want to refresh the live demo.
    """
    _wipe_all()
    _insert_demo()
    print("✅ Demo data reset and re-seeded.")
