import os, pathlib, datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, select, func, ForeignKey, String, Integer, Date, DateTime, Float
from sqlalchemy.orm import Session, DeclarativeBase, Mapped, mapped_column, relationship
from dotenv import load_dotenv

BASE_DIR = pathlib.Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

class Base(DeclarativeBase): pass

class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None]
    email: Mapped[str | None]
    address: Mapped[str | None]
    cases: Mapped[list["Case"]] = relationship(back_populates="client")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="client")

class CaseType(Base):
    __tablename__ = "case_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    cases: Mapped[list["Case"]] = relationship(back_populates="type")

class CaseStatus(Base):
    __tablename__ = "case_status"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    cases: Mapped[list["Case"]] = relationship(back_populates="status")

class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(50))
    title: Mapped[str]
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    type_id: Mapped[int] = mapped_column(ForeignKey("case_types.id"))
    status_id: Mapped[int] = mapped_column(ForeignKey("case_status.id"))
    next_hearing_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    client: Mapped["Client"] = relationship(back_populates="cases")
    type: Mapped["CaseType"] = relationship(back_populates="cases")
    status: Mapped["CaseStatus"] = relationship(back_populates="cases")

class Hearing(Base):
    __tablename__ = "hearings"
    id: Mapped[int] = mapped_column(primary_key=True)
    date_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    venue: Mapped[str | None]
    judge: Mapped[str | None]
    status: Mapped[str] = mapped_column(String(40), default="Scheduled")
    case: Mapped["Case"] = relationship()

class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40))
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    issue_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Draft")
    total_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    client: Mapped["Client"] = relationship(back_populates="invoices")
    case: Mapped["Case | None"] = relationship()

def make_engine():
    os.makedirs(BASE_DIR / "data", exist_ok=True)
    url = (os.getenv("DATABASE_URL") or "").strip()
    if url:
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url.split("postgresql://",1)[1]
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(select(1))
            print("Using DATABASE_URL:", url)
            return engine
        except Exception as e:
            print("DATABASE_URL invalid, falling back to SQLite:", e)
    sqlite_url = f"sqlite:///{BASE_DIR/'data'/'juris360.db'}"
    return create_engine(sqlite_url, pool_pre_ping=True)

engine = make_engine()
Base.metadata.create_all(engine)

def seed():
    from sqlalchemy import select
    with Session(engine) as s:
        if not s.scalar(select(func.count(Client.id))):
            s.add_all([
                Client(name="Amina Noor", phone="+254710909090", email="amina.noor@mail.com", address="Eastleigh"),
                Client(name="Blue Horizon SACCO", phone="+254740606060", email="finance@bluehorizon.co.ke", address="CBD"),
                Client(name="John Kamau", phone="+254721111222", address="Thika"),
                Client(name="Mwas Traders", phone="+254733444555", email="accounts@mwas.co.ke", address="Industrial Area"),
                Client(name="Rahab & Co. Ltd", phone="+254712345678", email="rahab@example.com", address="Westlands"),
            ])
        if not s.scalar(select(func.count(CaseType.id))):
            s.add_all([CaseType(name="Criminal"), CaseType(name="Family"), CaseType(name="Commercial")])
        if not s.scalar(select(func.count(CaseStatus.id))):
            s.add_all([CaseStatus(name="Open"), CaseStatus(name="Adjourned"), CaseStatus(name="Ongoing"), CaseStatus(name="Closed")])
        s.commit()
        if not s.scalar(select(func.count(Case.id))):
            t_crim = s.scalar(select(CaseType).where(CaseType.name=="Criminal"))
            t_fam  = s.scalar(select(CaseType).where(CaseType.name=="Family"))
            t_com  = s.scalar(select(CaseType).where(CaseType.name=="Commercial"))
            st_open = s.scalar(select(CaseStatus).where(CaseStatus.name=="Open"))
            st_adj  = s.scalar(select(CaseStatus).where(CaseStatus.name=="Adjourned"))
            st_on   = s.scalar(select(CaseStatus).where(CaseStatus.name=="Ongoing"))
            def gid(name): return s.scalar(select(Client.id).where(Client.name==name))
            s.add_all([
                Case(number="CRIM/045/2025", title="Charge: possession", client_id=gid("John Kamau"), type_id=t_crim.id, status_id=st_open.id, next_hearing_date=datetime.date(2025,9,3)),
                Case(number="FAM/018/2025", title="Custody application", client_id=gid("Amina Noor"), type_id=t_fam.id, status_id=st_adj.id, next_hearing_date=datetime.date(2025,9,5)),
                Case(number="COMM/001/2025", title="Supplier breach dispute", client_id=gid("Rahab & Co. Ltd"), type_id=t_com.id, status_id=st_on.id, next_hearing_date=datetime.date(2025,9,10)),
            ]); s.commit()
        if not s.scalar(select(func.count(Invoice.id))):
            c_am = s.scalar(select(Client).where(Client.name=="Amina Noor"))
            c_ra = s.scalar(select(Client).where(Client.name=="Rahab & Co. Ltd"))
            cc1 = s.scalar(select(Case).where(Case.number=="FAM/018/2025"))
            cc2 = s.scalar(select(Case).where(Case.number=="COMM/001/2025"))
            s.add_all([
                Invoice(number="J360-2025-0002", client_id=c_am.id, case_id=cc1.id if cc1 else None, issue_date=datetime.date(2025,8,22), due_date=datetime.date(2025,9,6), status="Draft", total_amount=9280.00),
                Invoice(number="J360-2025-0001", client_id=c_ra.id, case_id=cc2.id if cc2 else None, issue_date=datetime.date(2025,8,20), due_date=datetime.date(2025,9,4), status="Sent", total_amount=11460.00),
            ]); s.commit()
seed()

def counts():
    with Session(engine) as s:
        total_clients = s.scalar(select(func.count(Client.id))) or 0
        pending_cases = s.scalar(select(func.count(Case.id)).join(CaseStatus).where(CaseStatus.name.in_(["Open","Adjourned","Ongoing"]))) or 0
        pending_invoices = s.scalar(select(func.count(Invoice.id)).where(Invoice.status != "Paid")) or 0
        return {"clients": total_clients, "pending_cases": pending_cases, "pending_invoices": pending_invoices}

@app.get("/")
def home(): return redirect(url_for("dashboard"))

@app.get("/dashboard")
def dashboard(): return render_template("dashboard.html", counts=counts(), active="dashboard")

# Clients CRUD
@app.get("/clients")
def clients():
    with Session(engine) as s:
        items = s.scalars(select(Client).order_by(Client.name)).all()
    return render_template("clients.html", items=items, active="clients")

@app.route("/clients/new", methods=["GET","POST"])
def client_new():
    if request.method=="POST":
        with Session(engine) as s:
            s.add(Client(name=request.form["name"], phone=request.form.get("phone") or None, email=request.form.get("email") or None, address=request.form.get("address") or None)); s.commit()
        flash("Client created","success"); return redirect(url_for("clients"))
    return render_template("client_form.html", item=None, active="clients")

@app.route("/clients/<int:id>/edit", methods=["GET","POST"])
def client_edit(id:int):
    with Session(engine) as s:
        item = s.get(Client, id)
        if not item: flash("Client not found","error"); return redirect(url_for("clients"))
        if request.method=="POST":
            item.name=request.form["name"]; item.phone=request.form.get("phone") or None; item.email=request.form.get("email") or None; item.address=request.form.get("address") or None; s.commit(); flash("Client updated","success"); return redirect(url_for("clients"))
        s.expunge(item)
    return render_template("client_form.html", item=item, active="clients")

@app.get("/clients/<int:id>/delete")
def client_delete(id:int):
    with Session(engine) as s:
        item = s.get(Client, id)
        if item: s.delete(item); s.commit(); flash("Client deleted","success")
    return redirect(url_for("clients"))

# Lookups Types
@app.get("/lookups/types")
def lookups_types():
    with Session(engine) as s:
        items = s.scalars(select(CaseType).order_by(CaseType.name)).all()
    return render_template("lookups_types.html", items=items, active="lookups")

@app.route("/lookups/types/new", methods=["GET","POST"])
def lookup_type_new():
    if request.method=="POST":
        with Session(engine) as s: s.add(CaseType(name=request.form["name"])); s.commit()
        flash("Type created","success"); return redirect(url_for("lookups_types"))
    return render_template("lookup_form.html", item=None, label="Case Type", is_type=True, active="lookups")

@app.route("/lookups/types/<int:id>/edit", methods=["GET","POST"])
def lookup_type_edit(id:int):
    with Session(engine) as s:
        item = s.get(CaseType, id)
        if not item: flash("Type not found","error"); return redirect(url_for("lookups_types"))
        if request.method=="POST": item.name=request.form["name"]; s.commit(); flash("Type updated","success"); return redirect(url_for("lookups_types"))
        s.expunge(item)
    return render_template("lookup_form.html", item=item, label="Case Type", is_type=True, active="lookups")

@app.get("/lookups/types/<int:id>/delete")
def lookup_type_delete(id:int):
    with Session(engine) as s:
        item = s.get(CaseType, id)
        if item: s.delete(item); s.commit(); flash("Type deleted","success")
    return redirect(url_for("lookups_types"))

# Lookups Status
@app.get("/lookups/status")
def lookups_status():
    with Session(engine) as s:
        items = s.scalars(select(CaseStatus).order_by(CaseStatus.name)).all()
    return render_template("lookups_status.html", items=items, active="lookups")

@app.route("/lookups/status/new", methods=["GET","POST"])
def lookup_status_new():
    if request.method=="POST":
        with Session(engine) as s: s.add(CaseStatus(name=request.form["name"])); s.commit()
        flash("Status created","success"); return redirect(url_for("lookups_status"))
    return render_template("lookup_form.html", item=None, label="Case Status", is_type=False, active="lookups")

@app.route("/lookups/status/<int:id>/edit", methods=["GET","POST"])
def lookup_status_edit(id:int):
    with Session(engine) as s:
        item = s.get(CaseStatus, id)
        if not item: flash("Status not found","error"); return redirect(url_for("lookups_status"))
        if request.method=="POST": item.name=request.form["name"]; s.commit(); flash("Status updated","success"); return redirect(url_for("lookups_status"))
        s.expunge(item)
    return render_template("lookup_form.html", item=item, label="Case Status", is_type=False, active="lookups")

@app.get("/lookups/status/<int:id>/delete")
def lookup_status_delete(id:int):
    with Session(engine) as s:
        item = s.get(CaseStatus, id)
        if item: s.delete(item); s.commit(); flash("Status deleted","success")
    return redirect(url_for("lookups_status"))

# Cases
@app.get("/cases")
def cases():
    with Session(engine) as s:
        items = s.scalars(select(Case).order_by(Case.number)).all()
        for c in items: _ = c.client, c.type, c.status
    return render_template("cases.html", items=items, active="cases")

@app.route("/cases/new", methods=["GET","POST"])
def case_new():
    with Session(engine) as s:
        clients = s.scalars(select(Client).order_by(Client.name)).all()
        types = s.scalars(select(CaseType).order_by(CaseType.name)).all()
        status = s.scalars(select(CaseStatus).order_by(CaseStatus.name)).all()
        if request.method=="POST":
            next_dt = request.form.get("next_hearing_date") or None
            nh = datetime.date.fromisoformat(next_dt) if next_dt else None
            s.add(Case(number=request.form["number"], title=request.form["title"], client_id=int(request.form["client_id"]), type_id=int(request.form["type_id"]), status_id=int(request.form["status_id"]), next_hearing_date=nh))
            s.commit(); flash("Case created","success"); return redirect(url_for("cases"))
        return render_template("case_form.html", item=None, clients=clients, types=types, status=status, active="cases")

@app.route("/cases/<int:id>/edit", methods=["GET","POST"])
def case_edit(id:int):
    with Session(engine) as s:
        item = s.get(Case, id)
        if not item: flash("Case not found","error"); return redirect(url_for("cases"))
        clients = s.scalars(select(Client).order_by(Client.name)).all()
        types = s.scalars(select(CaseType).order_by(CaseType.name)).all()
        status = s.scalars(select(CaseStatus).order_by(CaseStatus.name)).all()
        if request.method=="POST":
            item.number=request.form["number"]; item.title=request.form["title"]
            item.client_id=int(request.form["client_id"]); item.type_id=int(request.form["type_id"]); item.status_id=int(request.form["status_id"])
            next_dt = request.form.get("next_hearing_date") or None
            item.next_hearing_date = datetime.date.fromisoformat(next_dt) if next_dt else None
            s.commit(); flash("Case updated","success"); return redirect(url_for("cases"))
        s.expunge(item)
        return render_template("case_form.html", item=item, clients=clients, types=types, status=status, active="cases")

@app.get("/cases/<int:id>/delete")
def case_delete(id:int):
    with Session(engine) as s:
        item = s.get(Case, id)
        if item: s.delete(item); s.commit(); flash("Case deleted","success")
    return redirect(url_for("cases"))

# Hearings
@app.get("/hearings")
def hearings():
    with Session(engine) as s:
        items = s.scalars(select(Hearing).order_by(Hearing.date_time)).all()
        for h in items: _ = h.case
    return render_template("hearings.html", items=items, active="hearings")

@app.route("/hearings/new", methods=["GET","POST"])
def hearing_new():
    with Session(engine) as s:
        cases = s.scalars(select(Case).order_by(Case.number)).all()
        if request.method=="POST":
            dt = request.form.get("date_time")
            dt_val = datetime.datetime.fromisoformat(dt) if dt else datetime.datetime.now()
            s.add(Hearing(date_time=dt_val, case_id=int(request.form["case_id"]), venue=request.form.get("venue") or None, judge=request.form.get("judge") or None, status=request.form.get("status") or "Scheduled"))
            s.commit(); flash("Hearing created","success"); return redirect(url_for("hearings"))
        return render_template("hearing_form.html", item=None, dtval="", cases=cases, active="hearings")

@app.route("/hearings/<int:id>/edit", methods=["GET","POST"])
def hearing_edit(id:int):
    with Session(engine) as s:
        item = s.get(Hearing, id)
        if not item: flash("Hearing not found","error"); return redirect(url_for("hearings"))
        cases = s.scalars(select(Case).order_by(Case.number)).all()
        if request.method=="POST":
            dt = request.form.get("date_time")
            item.date_time = datetime.datetime.fromisoformat(dt) if dt else item.date_time
            item.case_id = int(request.form["case_id"])
            item.venue = request.form.get("venue") or None
            item.judge = request.form.get("judge") or None
            item.status = request.form.get("status") or item.status
            s.commit(); flash("Hearing updated","success"); return redirect(url_for("hearings"))
        s.expunge(item)
        dtval = item.date_time.isoformat(timespec="minutes")
        return render_template("hearing_form.html", item=item, dtval=dtval, cases=cases, active="hearings")

@app.get("/hearings/<int:id>/delete")
def hearing_delete(id:int):
    with Session(engine) as s:
        item = s.get(Hearing, id)
        if item: s.delete(item); s.commit(); flash("Hearing deleted","success")
    return redirect(url_for("hearings"))

# Invoices
@app.get("/invoices")
def invoices():
    with Session(engine) as s:
        items = s.scalars(select(Invoice).order_by(Invoice.number)).all()
        for inv in items: _ = inv.client, inv.case
    return render_template("invoices.html", items=items, active="invoices")

@app.route("/invoices/new", methods=["GET","POST"])
def invoice_new():
    with Session(engine) as s:
        clients = s.scalars(select(Client).order_by(Client.name)).all()
        cases = s.scalars(select(Case).order_by(Case.number)).all()
        if request.method=="POST":
            cid = request.form.get("case_id") or None
            s.add(Invoice(number=request.form["number"], client_id=int(request.form["client_id"]), case_id=int(cid) if cid else None, issue_date=datetime.date.fromisoformat(request.form.get("issue_date")) if request.form.get("issue_date") else None, due_date=datetime.date.fromisoformat(request.form.get("due_date")) if request.form.get("due_date") else None, status=request.form.get("status") or "Draft", total_amount=float(request.form.get("total_amount") or 0)))
            s.commit(); flash("Invoice created","success"); return redirect(url_for("invoices"))
        return render_template("invoice_form.html", item=None, clients=clients, cases=cases, active="invoices")

@app.route("/invoices/<int:id>/edit", methods=["GET","POST"])
def invoice_edit(id:int):
    with Session(engine) as s:
        item = s.get(Invoice, id)
        if not item: flash("Invoice not found","error"); return redirect(url_for("invoices"))
        clients = s.scalars(select(Client).order_by(Client.name)).all()
        cases = s.scalars(select(Case).order_by(Case.number)).all()
        if request.method=="POST":
            item.number=request.form["number"]; item.client_id=int(request.form["client_id"])
            cid = request.form.get("case_id") or None; item.case_id = int(cid) if cid else None
            item.issue_date = datetime.date.fromisoformat(request.form.get("issue_date")) if request.form.get("issue_date") else None
            item.due_date = datetime.date.fromisoformat(request.form.get("due_date")) if request.form.get("due_date") else None
            item.status = request.form.get("status") or item.status
            item.total_amount = float(request.form.get("total_amount") or 0)
            s.commit(); flash("Invoice updated","success"); return redirect(url_for("invoices"))
        s.expunge(item)
        return render_template("invoice_form.html", item=item, clients=clients, cases=cases, active="invoices")

@app.get("/invoices/<int:id>/delete")
def invoice_delete(id:int):
    with Session(engine) as s:
        item = s.get(Invoice, id)
        if item: s.delete(item); s.commit(); flash("Invoice deleted","success")
    return redirect(url_for("invoices"))

if __name__ == "__main__":
    app.run(debug=True)
