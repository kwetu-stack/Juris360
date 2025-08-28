from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from ..models import Case, Client, CaseStatus
from .. import db

bp = Blueprint("cases", __name__)

@bp.route("/")
@login_required
def list_cases():
    q=(request.args.get("q") or "").strip()
    status_id=(request.args.get("status_id") or "")
    statuses=CaseStatus.query.order_by(CaseStatus.name.asc()).all()
    query=Case.query
    if q:
        like=f"%{q}%"; query=query.filter(Case.title.ilike(like))
    if status_id:
        query=query.filter_by(status_id=int(status_id))
    cases=query.order_by(Case.id.desc()).all()
    return render_template("view-cases.html", cases=cases, statuses=statuses, status_id=status_id, q=q)

@bp.route("/add", methods=["GET","POST"])
@login_required
def add_case():
    clients=Client.query.order_by(Client.name.asc()).all()
    statuses=CaseStatus.query.order_by(CaseStatus.name.asc()).all()
    if request.method=="POST":
        title=(request.form.get("title") or "").strip()
        description=(request.form.get("description") or "").strip()
        client_id=request.form.get("client_id") or None
        status_id=request.form.get("status_id") or None
        if not title: flash("Title required","danger")
        else:
            db.session.add(Case(title=title, description=description, client_id=client_id, status_id=status_id))
            db.session.commit(); flash("Case added","success"); return redirect(url_for("cases.list_cases"))
    return render_template("add-case.html", clients=clients, statuses=statuses)

@bp.route("/<int:id>/edit", methods=["GET","POST"])
@login_required
def edit_case(id):
    case=Case.query.get_or_404(id)
    clients=Client.query.order_by(Client.name.asc()).all()
    statuses=CaseStatus.query.order_by(CaseStatus.name.asc()).all()
    if request.method=="POST":
        case.title=(request.form.get("title") or "").strip()
        case.description=(request.form.get("description") or "").strip()
        case.client_id=request.form.get("client_id") or None
        case.status_id=request.form.get("status_id") or None
        if not case.title: flash("Title required","danger")
        else:
            db.session.commit(); flash("Case updated","success"); return redirect(url_for("cases.list_cases"))
    return render_template("add-case.html", case=case, clients=clients, statuses=statuses)

@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_case(id):
    c=Case.query.get_or_404(id); db.session.delete(c); db.session.commit()
    flash("Case deleted","info"); return redirect(url_for("cases.list_cases"))
