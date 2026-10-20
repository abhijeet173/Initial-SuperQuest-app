import json
from functools import wraps

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.admin import bp
from app.extensions import db
from app.models import Achievement, Mission, MissionAttempt, Profile, User


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@bp.get("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html", title="Operations", users=User.query.order_by(User.created_at.desc()).all(), missions=Mission.query.order_by(Mission.id).all(), attempts=MissionAttempt.query.order_by(MissionAttempt.started_at.desc()).limit(100).all(), user_count=User.query.count(), attempt_count=MissionAttempt.query.count(), total_score=db.session.query(db.func.coalesce(db.func.sum(Profile.total_score), 0)).scalar(), achievements=Achievement.query.order_by(Achievement.id).all())


@bp.post("/missions")
@admin_required
def create_mission():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    difficulty = request.form.get("difficulty", "Rookie")
    reward = request.form.get("base_reward", type=int)
    limit = request.form.get("time_limit", type=int)
    if not title or not description or difficulty not in {"Rookie", "Veteran", "Elite"} or not reward or not limit or reward < 1 or limit < 30:
        flash("Enter a title, description, valid difficulty, reward, and time limit (at least 30 seconds).", "error")
    elif Mission.query.filter_by(title=title).first():
        flash("A mission already uses that title.", "error")
    else:
        questions = json.loads(Mission.query.first().questions_json) if Mission.query.first() else []
        if not questions:
            flash("Seed the starter content before creating missions.", "error")
            return redirect(url_for("admin.dashboard"))
        db.session.add(Mission(title=title, description=description, difficulty=difficulty, base_reward=reward, time_limit=limit, questions_json=json.dumps(questions)))
        db.session.commit()
        flash("Mission created.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.post("/missions/<int:mission_id>/toggle")
@admin_required
def toggle_mission(mission_id):
    mission = db.session.get(Mission, mission_id)
    if not mission:
        abort(404)
    mission.active = not mission.active
    db.session.commit()
    flash(f"{mission.title} is now {'active' if mission.active else 'inactive'}.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.post("/missions/<int:mission_id>/delete")
@admin_required
def delete_mission(mission_id):
    mission = db.session.get(Mission, mission_id)
    if not mission:
        abort(404)
    db.session.delete(mission)
    db.session.commit()
    flash("Mission and its attempt history were removed.", "info")
    return redirect(url_for("admin.dashboard"))


@bp.post("/users/<int:user_id>/toggle")
@admin_required
def toggle_user(user_id):
    user = db.session.get(User, user_id)
    if not user or user.id == current_user.id or user.role == "admin":
        abort(404)
    user.is_active = not user.is_active
    db.session.commit()
    flash(f"{user.username} account is now {'active' if user.is_active else 'disabled'}.", "success")
    return redirect(url_for("admin.dashboard"))