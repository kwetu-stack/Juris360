from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from ..models import Event, EventType
from .. import db

bp = Blueprint("schedule", __name__)

@bp.route("/")
@login_required
def list_events():
    events=Event.query.order_by(Event.id.desc()).all()
    types=EventType.query.order_by(EventType.name.asc()).all()
    return render_template("schedule.html", events=events, types=types)

@bp.route("/add", methods=["GET","POST"])
@login_required
def add_event():
    types=EventType.query.order_by(EventType.name.asc()).all()
    if request.method=="POST":
        date=(request.form.get("date") or "").strip()
        description=(request.form.get("description") or "").strip()
        type_id=(request.form.get("type_id") or None)
        db.session.add(Event(date=date, description=description, type_id=type_id))
        db.session.commit(); flash("Event added.","success"); return redirect(url_for("schedule.list_events"))
    return render_template("add-event.html", types=types)

@bp.route("/<int:id>/edit", methods=["GET","POST"])
@login_required
def edit_event(id):
    ev=Event.query.get_or_404(id)
    types=EventType.query.order_by(EventType.name.asc()).all()
    if request.method=="POST":
        ev.date=(request.form.get("date") or "").strip()
        ev.description=(request.form.get("description") or "").strip()
        ev.type_id=(request.form.get("type_id") or None)
        db.session.commit(); flash("Event updated.","success"); return redirect(url_for("schedule.list_events"))
    return render_template("add-event.html", event=ev, types=types)

@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_event(id):
    ev=Event.query.get_or_404(id); db.session.delete(ev); db.session.commit()
    flash("Event deleted.","info"); return redirect(url_for("schedule.list_events"))
