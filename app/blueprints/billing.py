from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from ..models import Invoice, Client, BillingStatus
from .. import db

bp = Blueprint("billing", __name__)

@bp.route("/")
@login_required
def list_invoices():
    invoices=Invoice.query.order_by(Invoice.id.desc()).all()
    statuses=BillingStatus.query.order_by(BillingStatus.name.asc()).all()
    return render_template("billing.html", invoices=invoices, statuses=statuses)

@bp.route("/add", methods=["GET","POST"])
@login_required
def add_invoice():
    clients=Client.query.order_by(Client.name.asc()).all()
    statuses=BillingStatus.query.order_by(BillingStatus.name.asc()).all()
    if request.method=="POST":
        client_id=request.form.get("client_id") or None
        amount=float(request.form.get("amount") or 0)
        status_id=request.form.get("status_id") or None
        notes=(request.form.get("notes") or "").strip()
        db.session.add(Invoice(client_id=client_id, amount=amount, status_id=status_id, notes=notes))
        db.session.commit(); flash("Invoice saved.","success"); return redirect(url_for("billing.list_invoices"))
    return render_template("add-invoice.html", clients=clients, statuses=statuses)

@bp.route("/<int:id>/edit", methods=["GET","POST"])
@login_required
def edit_invoice(id):
    inv=Invoice.query.get_or_404(id)
    clients=Client.query.order_by(Client.name.asc()).all()
    statuses=BillingStatus.query.order_by(BillingStatus.name.asc()).all()
    if request.method=="POST":
        inv.client_id=request.form.get("client_id") or None
        inv.amount=float(request.form.get("amount") or 0)
        inv.status_id=request.form.get("status_id") or None
        inv.notes=(request.form.get("notes") or "").strip()
        db.session.commit(); flash("Invoice updated.","success"); return redirect(url_for("billing.list_invoices"))
    return render_template("add-invoice.html", invoice=inv, clients=clients, statuses=statuses)

@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_invoice(id):
    inv=Invoice.query.get_or_404(id); db.session.delete(inv); db.session.commit()
    flash("Invoice deleted.","info"); return redirect(url_for("billing.list_invoices"))
