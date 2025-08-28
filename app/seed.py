# app/seed.py
from datetime import date
from sqlalchemy import inspect
from app.models import db, Client, Case, Invoice, Event, Document

# ---------- helpers ----------

def _cols(model_cls):
    return set(inspect(model_cls).columns.keys())

def _has_col(model_cls, name: str) -> bool:
    return name in _cols(model_cls)

def _kw_for_model(model_cls, **pairs):
    """Filter kwargs to real table columns only (avoid relationships)."""
    allowed = _cols(model_cls)
    return {k: v for k, v in pairs.items() if k in allowed}

def _iso(d):
    return d.isoformat() if isinstance(d, date) else d

def _commit():
    db.session.commit()

def _add_all(objs):
    db.session.add_all(objs)
    _commit()

# ---------- public API ----------

def run_seed():
    """Idempotent seed (columns-only, FK-only linking)."""
    if Client.query.count() > 0:
        print("Seed skipped: Clients already exist.")
        return

    # ---- Clients ----
    clients_data = [
        dict(name="John Mwangi",  contact="+254712345678", email="john@example.com"),
        dict(name="Mary Atieno",  contact="+254733112233", email="mary@example.com"),
        dict(name="Acme Supplies Ltd", contact="+254701998877", email="info@acme.co.ke"),
    ]
    clients = [Client(**_kw_for_model(Client, **d)) for d in clients_data]
    _add_all(clients)

    # ---- Cases ----
    c1 = dict(title="CIV 55/2025", description="Breach of contract", status="Open")
    c2 = dict(title="HCC 102/2025", description="Land dispute", status="Pending")
    if _has_col(Case, "client_id"):
        c1["client_id"] = clients[0].id
        c2["client_id"] = clients[1].id
    cases = [Case(**_kw_for_model(Case, **c1)), Case(**_kw_for_model(Case, **c2))]
    _add_all(cases)

    # ---- Invoices ----
    i1 = dict(amount=50000, status="Unpaid", notes="Legal fees advance")
    i2 = dict(amount=20000, status="Paid",   notes="Filing fee")
    if _has_col(Invoice, "client_id"):
        i1["client_id"] = clients[0].id
        i2["client_id"] = clients[1].id
    elif _has_col(Invoice, "client"):  # string field variant
        i1["client"] = clients[0].name
        i2["client"] = clients[1].name
    invs = [Invoice(**_kw_for_model(Invoice, **i1)), Invoice(**_kw_for_model(Invoice, **i2))]
    _add_all(invs)

    # ---- Events ----
    ev_data = [
        dict(date=_iso(date(2025, 9, 1)),  description="Court Mention - Case CIV 55/2025"),
        dict(date=_iso(date(2025, 9,10)),  description="Client meeting - Mary Atieno"),
    ]
    if _has_col(Event, "type"):
        ev_data[0]["type"] = "Court"
        ev_data[1]["type"] = "Meeting"
    events = [Event(**_kw_for_model(Event, **d)) for d in ev_data]
    _add_all(events)

    # ---- Documents ----
    d1 = dict(title="Pleading Example", filename="pleading.pdf")
    d2 = dict(title="Invoice Sample",   filename="invoice.pdf")
    if _has_col(Document, "case_id"):
        d1["case_id"] = cases[0].id
        d2["case_id"] = cases[1].id
    docs = [Document(**_kw_for_model(Document, **d1)),
            Document(**_kw_for_model(Document, **d2))]
    _add_all(docs)

    print("✅ Demo data seeded.")

def run_seed_force():
    """Wipe demo tables and re-seed."""
    try:
        # children before parents
        if Document.query.count(): Document.query.delete(synchronize_session=False)
        if Invoice.query.count():  Invoice.query.delete(synchronize_session=False)
        if Case.query.count():     Case.query.delete(synchronize_session=False)
        if Event.query.count():    Event.query.delete(synchronize_session=False)
        if Client.query.count():   Client.query.delete(synchronize_session=False)
        _commit()
        print("🧹 Demo tables cleared.")
        run_seed()
        print("✅ Demo data force-reset and re-seeded.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Force seed failed: {e}")
        raise
