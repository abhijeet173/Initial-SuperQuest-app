import re

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.auth import bp
from app.extensions import db
from app.models import Profile, User


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not re.fullmatch(r"[A-Za-z0-9_]{3,24}", username):
            flash("Username must be 3-24 letters, numbers, or underscores.", "error")
        elif len(password) < 8:
            flash("Choose a password with at least 8 characters.", "error")
        elif password != confirm:
            flash("Those passwords do not match.", "error")
        elif User.query.filter(db.or_(User.username.ilike(username), User.email == email)).first():
            flash("That username or email is already in use.", "error")
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            user.profile = Profile()
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome to the team. Your first mission is ready.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html", title="Join the team")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        user = User.query.filter(db.or_(User.username.ilike(identity), User.email == identity.lower())).first()
        if user and user.is_active and user.check_password(request.form.get("password", "")):
            login_user(user, remember=bool(request.form.get("remember")))
            return redirect(request.args.get("next") or url_for("main.dashboard"))
        flash("We couldn't verify that login. Check your details and try again.", "error")
    return render_template("auth/login.html", title="Log in")


@bp.post("/logout")
def logout():
    logout_user()
    flash("You have safely signed out.", "info")
    return redirect(url_for("main.index"))