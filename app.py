# Juris360 v1 — fixed DB init (single SQLAlchemy instance, clean fallback)

import os
from datetime import datetime, date
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, create_engine

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-juris360')

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def _sqlite_uri():
    return 'sqlite:///' + os.path.join(DATA_DIR, 'juris360.db')

def _resolve_db_uri():
    url = os.getenv('DATABASE_URL', '').strip()
    if not url:
        return _sqlite_uri()
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif url.startswith('postgresql://') and '+psycopg' not in url:
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url

# ---- Pick a working DB URL (test first) ----
candidate_uri = _resolve_db_uri()
try:
    eng = create_engine(candidate_uri, pool_pre_ping=True, future=True)
    with eng.connect() as conn:
        conn.execute(text('SELECT 1'))
    db_uri = candidate_uri
except Exception:
    db_uri = _sqlite_uri()

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Single instance; bind once
db = SQLAlchemy()
db.init_app(app)

# ---------------- Models ----------------
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    address = db.Column(db.String(200))
    cases = db.relationship('Case', back_populates='client', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', back_populates='client', cascade='all, delete-orphan')

class CaseType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    cases = db.relationship('Case', back_populates='case_type')

class CaseStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    cases = db.relationship('Case', back_populates='status')
    hearings = db.relationship('Hearing', back_populates='status')
    invoices = db.relationship('Invoice', back_populates='status')

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ref = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    case_type_id = db.Column(db.Integer, db.ForeignKey('case_type.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('case_status.id'), nullable=False)
    opened_on = db.Column(db.Date, default=date.today)
    next_hearing_date = db.Column(db.Date, nullable=True)

    client = db.relationship('Client', back_populates='cases')
    case_type = db.relationship('CaseType', back_populates='cases')
    status = db.relationship('CaseStatus', back_populates='cases')
    hearings = db.relationship('Hearing', back_populates='case', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', back_populates='case', cascade='all, delete-orphan')

class Hearing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('case_status.id'), nullable=False)
    notes = db.Column(db.String(400))

    case = db.relationship('Case', back_populates='hearings')
    status = db.relationship('CaseStatus', back_populates='hearings')

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(40), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('case_status.id'), nullable=False)
    amount = db.Column(db.Numeric(12,2), nullable=False)
    due_date = db.Column(db.Date, nullable=True)

    client = db.relationship('Client', back_populates='invoices')
    case = db.relationship('Case', back_populates='invoices')
    status = db.relationship('CaseStatus', back_populates='invoices')

# ---------------- Seed ----------------
def seed_if_empty():
    if Client.query.first():
        return
    pending = CaseStatus(name='Pending')
    open_s = CaseStatus(name='Open')
    closed = CaseStatus(name='Closed')
    db.session.add_all([pending, open_s, closed])

    civil = CaseType(name='Civil')
    criminal = CaseType(name='Criminal')
    commercial = CaseType(name='Commercial')
    db.session.add_all([civil, criminal, commercial])

    alice = Client(name='Alice Wanjiku', phone='+254700000001', email='alice@example.com', address='Nairobi')
    bob = Client(name='Bob Otieno', phone='+254700000002', email='bob@example.com', address='Mombasa')
    db.session.add_all([alice, bob])
    db.session.flush()

    c1 = Case(ref='C-001', title='Contract Dispute', client=alice, case_type=commercial, status=pending)
    c2 = Case(ref='C-002', title='Property Claim', client=bob, case_type=civil, status=open_s)
    db.session.add_all([c1, c2])
    db.session.flush()

    h1 = Hearing(case=c1, date=date.today(), status=pending, notes='Mention')
    h2 = Hearing(case=c2, date=date.today(), status=open_s, notes='First hearing')
    db.session.add_all([h1, h2])

    i1 = Invoice(number='INV-1001', client=alice, case=c1, status=pending, amount=15000, due_date=date.today())
    i2 = Invoice(number='INV-1002', client=bob, case=c2, status=open_s, amount=22000, due_date=date.today())
    db.session.add_all([i1, i2])
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_if_empty()

# ---------------- Helpers ----------------
def _metrics():
    clients = Client.query.count()
    pending_cases = Case.query.join(CaseStatus).filter(CaseStatus.name.in_(['Pending','Open'])).count()
    pending_invoices = Invoice.query.join(CaseStatus).filter(CaseStatus.name.in_(['Pending','Open'])).count()
    return {'clients': clients, 'pending_cases': pending_cases, 'pending_invoices': pending_invoices}

# ---------------- Routes ----------------
@app.route('/')
def dashboard():
    recent = Case.query.order_by(Case.id.desc()).limit(5).all()
    return render_template('dashboard.html', active='dashboard', metrics=_metrics(), recent_cases=recent)

# ---- Clients CRUD ----
@app.route('/clients')
def clients():
    rows = Client.query.order_by(Client.name.asc()).all()
    return render_template('clients.html', active='clients', rows=rows, edit=None)

@app.route('/clients/new', methods=['POST'])
def clients_create():
    r = Client(name=request.form['name'], phone=request.form.get('phone'), email=request.form.get('email'), address=request.form.get('address'))
    db.session.add(r); db.session.commit()
    flash('Client created')
    return redirect(url_for('clients'))

@app.route('/clients/<int:id>/edit')
def clients_edit(id):
    rows = Client.query.order_by(Client.name.asc()).all()
    edit = Client.query.get_or_404(id)
    return render_template('clients.html', active='clients', rows=rows, edit=edit)

@app.route('/clients/<int:id>/update', methods=['POST'])
def clients_update(id):
    r = Client.query.get_or_404(id)
    r.name = request.form['name']; r.phone = request.form.get('phone'); r.email = request.form.get('email'); r.address = request.form.get('address')
    db.session.commit(); flash('Client updated')
    return redirect(url_for('clients'))

@app.route('/clients/<int:id>/delete', methods=['POST'])
def clients_delete(id):
    r = Client.query.get_or_404(id); db.session.delete(r); db.session.commit(); flash('Client deleted')
    return redirect(url_for('clients'))

# ---- Lookups ----
@app.route('/lookups')
def lookups():
    return render_template('lookups.html', active='lookups',
        case_types=CaseType.query.order_by(CaseType.name).all(),
        case_status=CaseStatus.query.order_by(CaseStatus.name).all(),
        edit=None, edit_entity=None)

@app.route('/lookups/case-types/new', methods=['POST'])
def case_types_create():
    db.session.add(CaseType(name=request.form['name'])); db.session.commit(); flash('Case type added')
    return redirect(url_for('lookups'))

@app.route('/lookups/case-types/<int:id>/edit')
def case_types_edit(id):
    return render_template('lookups.html', active='lookups',
        case_types=CaseType.query.order_by(CaseType.name).all(),
        case_status=CaseStatus.query.order_by(CaseStatus.name).all(),
        edit=CaseType.query.get_or_404(id), edit_entity='type')

@app.route('/lookups/case-types/<int:id>/update', methods=['POST'])
def case_types_update(id):
    r = CaseType.query.get_or_404(id); r.name = request.form['name']; db.session.commit(); flash('Case type updated')
    return redirect(url_for('lookups'))

@app.route('/lookups/case-types/<int:id>/delete', methods=['POST'])
def case_types_delete(id):
    r = CaseType.query.get_or_404(id); db.session.delete(r); db.session.commit(); flash('Case type deleted')
    return redirect(url_for('lookups'))

@app.route('/lookups/case-status/new', methods=['POST'])
def case_status_create():
    db.session.add(CaseStatus(name=request.form['name'])); db.session.commit(); flash('Case status added')
    return redirect(url_for('lookups'))

@app.route('/lookups/case-status/<int:id>/edit')
def case_status_edit(id):
    return render_template('lookups.html', active='lookups',
        case_types=CaseType.query.order_by(CaseType.name).all(),
        case_status=CaseStatus.query.order_by(CaseStatus.name).all(),
        edit=CaseStatus.query.get_or_404(id), edit_entity='status')

@app.route('/lookups/case-status/<int:id>/update', methods=['POST'])
def case_status_update(id):
    r = CaseStatus.query.get_or_404(id); r.name = request.form['name']; db.session.commit(); flash('Case status updated')
    return redirect(url_for('lookups'))

@app.route('/lookups/case-status/<int:id>/delete', methods=['POST'])
def case_status_delete(id):
    r = CaseStatus.query.get_or_404(id); db.session.delete(r); db.session.commit(); flash('Case status deleted')
    return redirect(url_for('lookups'))

# ---- Cases ----
@app.route('/cases')
def cases():
    rows = Case.query.order_by(Case.id.desc()).all()
    return render_template('cases.html', active='cases', rows=rows,
        clients=Client.query.order_by(Client.name).all(),
        types=CaseType.query.order_by(CaseType.name).all(),
        status=CaseStatus.query.order_by(CaseStatus.name).all(),
        edit=None)

@app.route('/cases/new', methods=['POST'])
def cases_create():
    r = Case(
        ref=request.form['ref'], title=request.form['title'],
        client_id=int(request.form['client_id']),
        case_type_id=int(request.form['case_type_id']),
        status_id=int(request.form['status_id'])
    )
    db.session.add(r); db.session.commit(); flash('Case created')
    return redirect(url_for('cases'))

@app.route('/cases/<int:id>/edit')
def cases_edit(id):
    rows = Case.query.order_by(Case.id.desc()).all()
    return render_template('cases.html', active='cases', rows=rows,
        clients=Client.query.order_by(Client.name).all(),
        types=CaseType.query.order_by(CaseType.name).all(),
        status=CaseStatus.query.order_by(CaseStatus.name).all(),
        edit=Case.query.get_or_404(id))

@app.route('/cases/<int:id>/update', methods=['POST'])
def cases_update(id):
    r = Case.query.get_or_404(id)
    r.ref=request.form['ref']; r.title=request.form['title']
    r.client_id=int(request.form['client_id']); r.case_type_id=int(request.form['case_type_id']); r.status_id=int(request.form['status_id'])
    db.session.commit(); flash('Case updated')
    return redirect(url_for('cases'))

@app.route('/cases/<int:id>/delete', methods=['POST'])
def cases_delete(id):
    r = Case.query.get_or_404(id); db.session.delete(r); db.session.commit(); flash('Case deleted')
    return redirect(url_for('cases'))

# ---- Hearings ----
@app.route('/hearings')
def hearings():
    rows = Hearing.query.order_by(Hearing.date.desc()).all()
    return render_template('hearings.html', active='hearings', rows=rows,
        cases=Case.query.order_by(Case.id.desc()).all(),
        status=CaseStatus.query.order_by(CaseStatus.name).all(),
        edit=None)

@app.route('/hearings/new', methods=['POST'])
def hearings_create():
    r = Hearing(
        case_id=int(request.form['case_id']),
        date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
        status_id=int(request.form['status_id']),
        notes=request.form.get('notes')
    )
    db.session.add(r); db.session.commit(); flash('Hearing added')
    return redirect(url_for('hearings'))

@app.route('/hearings/<int:id>/edit')
def hearings_edit(id):
    rows = Hearing.query.order_by(Hearing.date.desc()).all()
    return render_template('hearings.html', active='hearings', rows=rows,
        cases=Case.query.order_by(Case.id.desc()).all(),
        status=CaseStatus.query.order_by(CaseStatus.name).all(),
        edit=Hearing.query.get_or_404(id))

@app.route('/hearings/<int:id>/update', methods=['POST'])
def hearings_update(id):
    r = Hearing.query.get_or_404(id)
    r.case_id=int(request.form['case_id'])
    r.date=datetime.strptime(request.form['date'], '%Y-%m-%d').date()
    r.status_id=int(request.form['status_id'])
    r.notes=request.form.get('notes')
    db.session.commit(); flash('Hearing updated')
    return redirect(url_for('hearings'))

@app.route('/hearings/<int:id>/delete', methods=['POST'])
def hearings_delete(id):
    r = Hearing.query.get_or_404(id); db.session.delete(r); db.session.commit(); flash('Hearing deleted')
    return redirect(url_for('hearings'))

# ---- Invoices ----
@app.route('/invoices')
def invoices():
    rows = Invoice.query.order_by(Invoice.id.desc()).all()
    return render_template('invoices.html', active='invoices', rows=rows,
        clients=Client.query.order_by(Client.name).all(),
        cases=Case.query.order_by(Case.id.desc()).all(),
        status=CaseStatus.query.order_by(CaseStatus.name).all(),
        edit=None)

@app.route('/invoices/new', methods=['POST'])
def invoices_create():
    r = Invoice(
        number=request.form['number'],
        client_id=int(request.form['client_id']),
        case_id=int(request.form['case_id']),
        status_id=int(request.form['status_id']),
        amount=request.form.get('amount', 0),
        due_date=datetime.strptime(request.form['due_date'], '%Y-%m-%d').date() if request.form.get('due_date') else None
    )
    db.session.add(r); db.session.commit(); flash('Invoice created')
    return redirect(url_for('invoices'))

@app.route('/invoices/<int:id>/edit')
def invoices_edit(id):
    rows = Invoice.query.order_by(Invoice.id.desc()).all()
    return render_template('invoices.html', active='invoices', rows=rows,
        clients=Client.query.order_by(Client.name).all(),
        cases=Case.query.order_by(Case.id.desc()).all(),
        status=CaseStatus.query.order_by(CaseStatus.name).all(),
        edit=Invoice.query.get_or_404(id))

@app.route('/invoices/<int:id>/update', methods=['POST'])
def invoices_update(id):
    r = Invoice.query.get_or_404(id)
    r.number=request.form['number']
    r.client_id=int(request.form['client_id'])
    r.case_id=int(request.form['case_id'])
    r.status_id=int(request.form['status_id'])
    r.amount=request.form.get('amount', 0)
    r.due_date=datetime.strptime(request.form['due_date'], '%Y-%m-%d').date() if request.form.get('due_date') else None
    db.session.commit(); flash('Invoice updated')
    return redirect(url_for('invoices'))

@app.route('/invoices/<int:id>/delete', methods=['POST'])
def invoices_delete(id):
    r = Invoice.query.get_or_404(id); db.session.delete(r); db.session.commit(); flash('Invoice deleted')
    return redirect(url_for('invoices'))

if __name__ == '__main__':
    app.run(debug=True)
