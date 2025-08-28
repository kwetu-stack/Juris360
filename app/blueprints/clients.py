from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from ..models import Client
from .. import db

bp = Blueprint("clients", __name__)

@bp.route("/")
@login_required
def list_clients():
    q=(request.args.get("q") or "").strip()
    query=Client.query
    if q:
        like=f"%{q}%"
        query=query.filter((Client.name.ilike(like)) | (Client.email.ilike(like)))
    clients=query.order_by(Client.id.desc()).all()
    return render_template("view-clients.html", clients=clients, q=q)

@bp.route("/add", methods=["GET","POST"])
@login_required
def add_client():
    if request.method=="POST":
        name=(request.form.get("name") or "").strip()
        contact=(request.form.get("contact") or "").strip()
        email=(request.form.get("email") or "").strip()
        if not name: flash("Name required","danger")
        else:
            db.session.add(Client(name=name, contact=contact, email=email))
            db.session.commit(); flash("Client added","success"); return redirect(url_for("clients.list_clients"))
    return render_template("add-client.html")

@bp.route("/<int:id>/edit", methods=["GET","POST"])
@login_required
def edit_client(id):
    c=Client.query.get_or_404(id)
    if request.method=="POST":
        c.name=(request.form.get("name") or "").strip()
        c.contact=(request.form.get("contact") or "").strip()
        c.email=(request.form.get("email") or "").strip()
        if not c.name: flash("Name required","danger")
        else:
            db.session.commit(); flash("Client updated","success"); return redirect(url_for("clients.list_clients"))
    return render_template("add-client.html", client=c)

@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_client(id):
    c=Client.query.get_or_404(id); db.session.delete(c); db.session.commit()
    flash("Client deleted","info"); return redirect(url_for("clients.list_clients"))
