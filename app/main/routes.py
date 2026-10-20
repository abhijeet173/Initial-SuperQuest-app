from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.main import bp
from app.models import Mission, MissionAttempt, Profile, Superpower, User, UserAchievement


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html", title="SuperQuest")


@bp.get("/dashboard")
@login_required
def dashboard():
    missions = Mission.query.filter_by(active=True).order_by(Mission.id).all()
    completed = MissionAttempt.query.filter_by(user_id=current_user.id, status="completed").order_by(MissionAttempt.completed_at.desc()).all()
    return render_template("game/dashboard.html", title="Command center", missions=missions, recent=completed[:3], completed_count=len(completed))


@bp.get("/powers")
@login_required
def powers():
    return render_template("game/powers.html", title="Choose your power", powers=Superpower.query.order_by(Superpower.id).all())


@bp.post("/powers")
@login_required
def select_power():
    power = db.session.get(Superpower, request.form.get("power_id", type=int))
    if not power:
        flash("Choose an available power.", "error")
    else:
        current_user.selected_power = power
        db.session.commit()
        flash(f"{power.name} is ready for action.", "success")
    return redirect(url_for("main.powers"))


@bp.get("/missions")
@login_required
def missions():
    all_missions = Mission.query.filter_by(active=True).order_by(Mission.id).all()
    complete_ids = {row[0] for row in db.session.query(MissionAttempt.mission_id).filter_by(user_id=current_user.id, status="completed").distinct()}
    return render_template("game/missions.html", title="Mission board", missions=all_missions, complete_ids=complete_ids)


@bp.get("/profile")
@login_required
def profile():
    attempts = MissionAttempt.query.filter_by(user_id=current_user.id, status="completed").order_by(MissionAttempt.completed_at.desc()).all()
    awards = UserAchievement.query.filter_by(user_id=current_user.id).order_by(UserAchievement.unlocked_at.desc()).all()
    return render_template("game/profile.html", title="Hero profile", attempts=attempts, awards=awards)


@bp.route("/leaderboard")
def leaderboard():
    leaders = User.query.join(Profile).filter(User.role == "player", User.is_active.is_(True)).order_by(Profile.total_score.desc(), Profile.level.desc(), User.username.asc()).limit(50).all()
    current_rank = None
    if current_user.is_authenticated and current_user.role == "player":
        ranked = User.query.join(Profile).filter(User.role == "player", User.is_active.is_(True)).order_by(Profile.total_score.desc(), Profile.level.desc(), User.username.asc()).all()
        current_rank = next((position for position, user in enumerate(ranked, 1) if user.id == current_user.id), None)
    return render_template("game/leaderboard.html", title="Leaderboard", leaders=leaders, current_rank=current_rank)