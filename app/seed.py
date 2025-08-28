from datetime import date
from app.models import db, Client, Case, Invoice, Event, Document

def run_seed():
    """Insert demo data if DB is empty. Safe to run multiple times."""
    # If there are already clients, assume the DB is seeded
    if Client.query.count() > 0:
        print("[AUTO_SEED] Data already present; skipping.")
        return

    # --- Demo Clients ---
    clients = [
        Client(name="John Mwangi", contact="+254712345678", email="john@example.com"),
        Client(name="Mary Atieno", contact="+254733112233", email="mary@example.com"),
        Client(name="Acme Supplies Ltd", contact="+254701998877", email="info@acme.co.ke"),
    ]
    db.session.add_all(clients)

    # Flush so IDs are available without a full commit
    db.session.flush()

    # --- Demo Cases ---
    cases = [
        Case(
            title="CIV 55/2025",
            description="Breach of contract",
            status="Open",
            client_id=clients[0].id,
        ),
        Case(
            title="HCC 102/2025",
            description="Land dispute",
            status="Pending",
            client_id=clients[1].id,
        ),
    ]
    db.session.add_all(cases)

    # --- Demo Invoices ---
    invoices = [
        Invoice(
            client_id=clients[0].id,  # <-- use FK, not name string
            amount=50000,
            status="Unpaid",
            notes="Legal fees advance",
        ),
        Invoice(
            client_id=clients[1].id,
            amount=20000,
            status="Paid",
            notes="Filing fee",
        ),
    ]
    db.session.add_all(invoices)

    # --- Demo Events ---
    events = [
        Event(date=date(2025, 9, 1), description="Court Mention - Case CIV 55/2025", type="Court"),
        Event(date=date(2025, 9, 10), description="Client meeting - Mary Atieno", type="Meeting"),
    ]
    db.session.add_all(events)

    # --- Demo Documents ---
    docs = [
        Document(title="Pleading Example", filename="pleading.pdf"),
        Document(title="Invoice Sample", filename="invoice.pdf"),
    ]
    db.session.add_all(docs)

    db.session.commit()
    print("[AUTO_SEED] ✅ Demo data seeded.")
