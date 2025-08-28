from flask_login import UserMixin
from datetime import datetime
from . import db, login_manager

# Lookup tables for dropdowns
class CaseStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

class DocType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

class BillingStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

class EventType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    def get_id(self): return str(self.id)

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(120))
    email = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status_id = db.Column(db.Integer, db.ForeignKey('case_status.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    client = db.relationship('Client')
    status = db.relationship('CaseStatus')

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    case_ref = db.Column(db.String(120))
    type_id = db.Column(db.Integer, db.ForeignKey('doc_type.id'))
    notes = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    size_bytes = db.Column(db.Integer, default=0)
    type = db.relationship('DocType')

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    amount = db.Column(db.Float, default=0.0)
    status_id = db.Column(db.Integer, db.ForeignKey('billing_status.id'))
    issued_on = db.Column(db.Date, default=datetime.utcnow)
    notes = db.Column(db.String(255))
    client = db.relationship('Client')
    status = db.relationship('BillingStatus')

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))  # YYYY-MM-DD
    description = db.Column(db.String(255))
    type_id = db.Column(db.Integer, db.ForeignKey('event_type.id'))
    type = db.relationship('EventType')
