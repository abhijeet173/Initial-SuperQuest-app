import json
import random
from datetime import datetime, timezone
from functools import wraps

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.game import bp
from app.models import Achievement, Mission, MissionAttempt, Profile, UserAchievement, utcnow


def public_questions(mission):
    questions = json.loads(mission.questions_json)
    return [{"prompt": q["prompt"], "choices": q["choices"]} for q in questions]


@bp.post("/start/<int:mission_id>")
@login_required
def start(mission_id):
    mission = db.session.get(Mission, mission_id)
    if not mission or not mission.active:
        abort(404)
    if not current_user.selected_power:
        flash("Choose a superpower before launching a mission.", "info")
        return redirect(url_for("main.powers"))
    attempt = MissionAttempt(user_id=current_user.id, mission_id=mission.id, power_name=current_user.selected_power.name)
    db.session.add(attempt)
    db.session.commit()
    return redirect(url_for("game.play", attempt_id=attempt.id))


@bp.get("/play/<int:attempt_id>")
@login_required
def play(attempt_id):
    attempt = db.session.get(MissionAttempt, attempt_id)
    if not attempt or attempt.user_id != current_user.id:
        abort(404)
    if attempt.status != "started":
        return redirect(url_for("game.result", attempt_id=attempt.id))
    return render_template("game/play.html", title=attempt.mission.title, attempt=attempt, questions=public_questions(attempt.mission))


@bp.post("/hint/<int:attempt_id>/<int:question_index>")
@login_required
def hint(attempt_id, question_index):
    from flask import jsonify
    attempt = db.session.get(MissionAttempt, attempt_id)
    if not attempt or attempt.user_id != current_user.id or attempt.status != "started":
        abort(404)
    questions = json.loads(attempt.mission.questions_json)
    if attempt.power_name != "Telekinesis" or attempt.hint_used or question_index < 0 or question_index >= len(questions):
        abort(403)
    correct = questions[question_index]["answer"]
    wrong = [index for index in range(len(questions[question_index]["choices"])) if index != correct]
    attempt.hint_used = True
    db.session.commit()
    return jsonify({"remove": random.choice(wrong)})


def unlock_achievements(user, attempt):
    completed_count = MissionAttempt.query.filter_by(user_id=user.id, status="completed").filter(MissionAttempt.score > 0).count()
    criteria_values = {
        "first": completed_count,
        "missions": completed_count,
        "score": user.profile.total_score,
        "perfect": int(attempt.correct_count == len(json.loads(attempt.mission.questions_json))),
    }
    existing = {entry.achievement_id for entry in UserAchievement.query.filter_by(user_id=user.id).all()}
    newly_unlocked = []
    for achievement in Achievement.query.all():
        if achievement.id not in existing and criteria_values.get(achievement.criteria, 0) >= achievement.threshold:
            db.session.add(UserAchievement(user_id=user.id, achievement_id=achievement.id))
            newly_unlocked.append(achievement)
    return newly_unlocked


@bp.post("/finish/<int:attempt_id>")
@login_required
def finish(attempt_id):
    attempt = db.session.get(MissionAttempt, attempt_id)
    if not attempt or attempt.user_id != current_user.id:
        abort(404)
    if attempt.status != "started":
        flash("This mission attempt has already been submitted.", "info")
        return redirect(url_for("game.result", attempt_id=attempt.id))

    questions = json.loads(attempt.mission.questions_json)
    raw_answers = [request.form.get(f"answer_{index}", "") for index in range(len(questions))]
    elapsed = max(0, (utcnow() - attempt.started_at).total_seconds())
    if elapsed > attempt.mission.time_limit + 15:
        correct = 0
        score = 0
        outcome = "expired"
    else:
        submitted = []
        try:
            submitted = [int(value) for value in raw_answers]
        except ValueError:
            submitted = []
        if len(submitted) != len(questions) or any(value < 0 or value > 3 for value in submitted):
            flash("The mission response was incomplete or invalid; no reward was issued.", "error")
            correct = 0
            score = 0
            outcome = "incomplete"
        else:
            correct = sum(answer == question["answer"] for answer, question in zip(submitted, questions))
            scoring_correct = correct
            score = round(attempt.mission.base_reward * scoring_correct / len(questions))
            if attempt.power_name == "Super Strength":
                score = round(score * 1.10)
            elif attempt.power_name == "Velocity":
                score += min(20, max(0, int((attempt.mission.time_limit - elapsed) / 5))) if correct else 0
            elif attempt.power_name == "Energy Shield":
                scoring_correct = min(len(questions), correct + 1) if correct >= len(questions) - 1 else correct
                score = round(attempt.mission.base_reward * scoring_correct / len(questions))
            elif attempt.power_name == "Elemental Control" and correct == len(questions):
                score = round(score * 1.15)
            outcome = "success" if correct == len(questions) else "partial"

    attempt.correct_count = correct
    attempt.score = score
    attempt.status = "completed"
    attempt.completed_at = utcnow()
    profile = current_user.profile
    profile.total_score += score
    profile.experience_points += score
    profile.level = profile.experience_points // 500 + 1
    unlocked = unlock_achievements(current_user, attempt)
    db.session.commit()
    return render_template("game/result.html", title="Mission report", attempt=attempt, outcome=outcome, unlocked=unlocked)


@bp.get("/result/<int:attempt_id>")
@login_required
def result(attempt_id):
    attempt = db.session.get(MissionAttempt, attempt_id)
    if not attempt or attempt.user_id != current_user.id or attempt.status != "completed":
        abort(404)
    total = len(json.loads(attempt.mission.questions_json))
    outcome = "success" if attempt.correct_count == total else "partial"
    return render_template("game/result.html", title="Mission report", attempt=attempt, outcome=outcome, unlocked=[])