from app.models import db, Client, Case, Invoice, Event, Document

def run_seed():
    """Insert demo data if DB is empty. Safe to run multiple times."""
    if Client.query.count() > 0:
        return  # already seeded

    # --- Demo Clients ---
    clients = [
        Client(name="John Mwangi", contact="+254712345678", email="john@example.com"),
        Client(name="Mary Atieno", contact="+254733112233", email="mary@example.com"),
        Client(name="Acme Supplies Ltd", contact="+254701998877", email="info@acme.co.ke"),
    ]
    db.session.add_all(clients)
    db.session.commit()

    # --- Demo Cases ---
    cases = [
        Case(title="CIV 55/2025", description="Breach of contract", status="Open", client_id=clients[0].id),
        Case(title="HCC 102/2025", description="Land dispute", status="Pending", client_id=clients[1].id),
    ]
    db.session.add_all(cases)

    # --- Demo Invoices ---
    invoices = [
        Invoice(client="John Mwangi", amount=50000, status="Unpaid", notes="Legal fees advance"),
        Invoice(client="Mary Atieno", amount=20000, status="Paid", notes="Filing fee"),
    ]
    db.session.add_all(invoices)

    # --- Demo Events ---
    events = [
        Event(date="2025-09-01", description="Court Mention - Case CIV 55/2025", type="Court"),
        Event(date="2025-09-10", description="Client meeting - Mary Atieno", type="Meeting"),
    ]
    db.session.add_all(events)

    # --- Demo Documents ---
    docs = [
        Document(title="Pleading Example", filename="pleading.pdf"),
        Document(title="Invoice Sample", filename="invoice.pdf"),
    ]
    db.session.add_all(docs)

    db.session.commit()
    print("✅ Demo data seeded.")
