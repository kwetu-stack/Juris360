from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User

bp = Blueprint("auth", __name__)

@bp.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("core.dashboard"))
    if request.method=="POST":
        u=(request.form.get("username") or "").strip()
        p=(request.form.get("password") or "").strip()
        user=User.query.filter_by(username=u).first()
        if user and user.password==p:
            login_user(user); flash("Login successful","success"); return redirect(url_for("core.dashboard"))
        flash("Invalid credentials","danger")
    return render_template("login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user(); flash("Logged out","info"); return redirect(url_for("auth.login"))
