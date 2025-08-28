# app/seed.py
from datetime import date
from sqlalchemy import inspect
from app.models import db, Client, Case, Invoice, Event, Document

# ---------- helpers ----------

def _has_column(model, col_name: str) -> bool:
    """Return True if the SQLAlchemy model has a column/relationship named col_name."""
    mapper = inspect(model)
    return (col_name in mapper.columns or col_name in mapper.relationships)

def _add_many(items):
    db.session.add_all(items)
    db.session.commit()

# ---------- public API ----------

def run_seed() -> None:
    """
    Insert demo data *only if* there are no clients yet.
    Safe to run multiple times.
    """
    try:
        if Client.query.count() > 0:
            print("Seed skipped: Clients already exist.")
            return

        # --- Clients ---
        clients = [
            Client(name="John Mwangi",  contact="+254712345678", email="john@example.com"),
            Client(name="Mary Atieno",  contact="+254733112233", email="mary@example.com"),
            Client(name="Acme Supplies Ltd", contact="+254701998877", email="info@acme.co.ke"),
        ]
        _add_many(clients)

        # --- Cases ---
        cases = [
            Case(
                title="CIV 55/2025",
                description="Breach of contract",
                status="Open",
                # works whether Case uses client_id FK or 'client' string
                **({"client_id": clients[0].id} if _has_column(Case, "client_id") else {"client": clients[0].name}),
            ),
            Case(
                title="HCC 102/2025",
                description="Land dispute",
                status="Pending",
                **({"client_id": clients[1].id} if _has_column(Case, "client_id") else {"client": clients[1].name}),
            ),
        ]
        _add_many(cases)

        # --- Invoices ---
        invoices = []
        if _has_column(Invoice, "client_id"):
            invoices = [
                Invoice(client_id=clients[0].id, amount=50000, status="Unpaid", notes="Legal fees advance"),
                Invoice(client_id=clients[1].id, amount=20000, status="Paid",   notes="Filing fee"),
            ]
        else:
            # fallback: simple string field 'client'
            invoices = [
                Invoice(client=clients[0].name, amount=50000, status="Unpaid", notes="Legal fees advance"),
                Invoice(client=clients[1].name, amount=20000, status="Paid",   notes="Filing fee"),
            ]
        _add_many(invoices)

        # --- Events ---
        # Use real date objects; works with Date columns (and is fine for Text columns too)
        events = [
            Event(date=date(2025, 9, 1),  description="Court Mention - Case CIV 55/2025",  **({"type": "Court"}   if _has_column(Event, "type") else {})),
            Event(date=date(2025, 9, 10), description="Client meeting - Mary Atieno",       **({"type": "Meeting"} if _has_column(Event, "type") else {})),
        ]
        _add_many(events)

        # --- Documents ---
        docs_kwargs_1 = {"title": "Pleading Example", "filename": "pleading.pdf"}
        docs_kwargs_2 = {"title": "Invoice Sample",   "filename": "invoice.pdf"}

        # If your Document has a FK to Case, attach it for nicer demos
        if _has_column(Document, "case_id"):
            docs_kwargs_1["case_id"] = cases[0].id
            docs_kwargs_2["case_id"] = cases[1].id

        docs = [Document(**docs_kwargs_1), Document(**docs_kwargs_2)]
        _add_many(docs)

        print("✅ Demo data seeded.")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Seed failed: {e}")
        raise


def run_seed_force() -> None:
    """
    Clear demo tables (keeps users/auth) and re-seed.
    Safe for demos; do not use in production data.
    """
    try:
        # Delete in dependency order (children first)
        # synchronize_session=False keeps this fast & cross-DB (SQLite/Postgres)
        if Document.query.count():
            Document.query.delete(synchronize_session=False)

        if Invoice.query.count():
            Invoice.query.delete(synchronize_session=False)

        if Case.query.count():
            Case.query.delete(synchronize_session=False)

        if Event.query.count():
            Event.query.delete(synchronize_session=False)

        if Client.query.count():
            Client.query.delete(synchronize_session=False)

        db.session.commit()
        print("🧹 Demo tables cleared.")

        run_seed()
        print("✅ Demo data force-reset and re-seeded.")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Force seed failed: {e}")
        raise
