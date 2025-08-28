from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint("core", __name__)

@bp.route("/")
def home():
    if current_user.is_authenticated: return redirect(url_for("core.dashboard"))
    return redirect(url_for("auth.login"))

@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user.username)
