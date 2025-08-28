# app/seed.py
from datetime import date
from sqlalchemy import inspect
from app.models import db, Client, Case, Invoice, Event, Document

# ---------- helpers ----------

def _has_column(model, name: str) -> bool:
    return name in inspect(model).columns

def _has_relationship(model, name: str) -> bool:
    return name in inspect(model).relationships

def _set_client_on(model_cls, obj_kwargs: dict, client_obj: Client):
    """
    Attach a client to kwargs for a model that may use:
      - client_id (FK int)
      - client (relationship to Client)
      - client (string column)
    """
    if _has_column(model_cls, "client_id"):
        obj_kwargs["client_id"] = client_obj.id
    elif _has_relationship(model_cls, "client"):
        obj_kwargs["client"] = client_obj  # relationship expects a Client instance
    elif _has_column(model_cls, "client"):
        obj_kwargs["client"] = client_obj.name  # plain string field
    # else: no client field; nothing to set

def _set_case_on_document(kwargs: dict, case_obj):
    if _has_column(Document, "case_id"):
        kwargs["case_id"] = case_obj.id
    elif _has_relationship(Document, "case"):
        kwargs["case"] = case_obj  # relationship

def _safe_date(value):
    """
    Use strings so it works whether Event.date is a Date or String column.
    """
    if isinstance(value, date):
        return value.isoformat()
    return value

def _add_many(items):
    db.session.add_all(items)
    db.session.commit()

# ---------- public API ----------

def run_seed() -> None:
    """
    Insert demo data only if there are no clients yet.
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
        cases = []
        case1 = {"title":"CIV 55/2025", "description":"Breach of contract", "status":"Open"}
        _set_client_on(Case, case1, clients[0])
        case2 = {"title":"HCC 102/2025", "description":"Land dispute", "status":"Pending"}
        _set_client_on(Case, case2, clients[1])
        cases = [Case(**case1), Case(**case2)]
        _add_many(cases)

        # --- Invoices ---
        inv1 = {"amount":50000, "status":"Unpaid", "notes":"Legal fees advance"}
        _set_client_on(Invoice, inv1, clients[0])
        inv2 = {"amount":20000, "status":"Paid",   "notes":"Filing fee"}
        _set_client_on(Invoice, inv2, clients[1])
        invoices = [Invoice(**inv1), Invoice(**inv2)]
        _add_many(invoices)

        # --- Events ---
        events = [
            Event(date=_safe_date(date(2025, 9, 1)),  description="Court Mention - Case CIV 55/2025",  **({"type":"Court"}   if _has_column(Event,"type") else {})),
            Event(date=_safe_date(date(2025, 9,10)),  description="Client meeting - Mary Atieno",       **({"type":"Meeting"} if _has_column(Event,"type") else {})),
        ]
        _add_many(events)

        # --- Documents ---
        d1 = {"title":"Pleading Example", "filename":"pleading.pdf"}
        d2 = {"title":"Invoice Sample",   "filename":"invoice.pdf"}
        if cases:
            _set_case_on_document(d1, cases[0])
            _set_case_on_document(d2, cases[1])
        docs = [Document(**d1), Document(**d2)]
        _add_many(docs)

        print("✅ Demo data seeded.")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Seed failed: {e}")
        raise


def run_seed_force() -> None:
    """
    Clear demo tables (keeps users/auth) and re-seed.
    """
    try:
        # Delete in child->parent order
        if Document.query.count(): Document.query.delete(synchronize_session=False)
        if Invoice.query.count():  Invoice.query.delete(synchronize_session=False)
        if Case.query.count():     Case.query.delete(synchronize_session=False)
        if Event.query.count():    Event.query.delete(synchronize_session=False)
        if Client.query.count():   Client.query.delete(synchronize_session=False)
        db.session.commit()
        print("🧹 Demo tables cleared.")

        run_seed()
        print("✅ Demo data force-reset and re-seeded.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Force seed failed: {e}")
        raise
