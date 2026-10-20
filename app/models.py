from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(24), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(12), nullable=False, default="player")
    selected_power_id = db.Column(db.Integer, db.ForeignKey("superpower.id"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    profile = db.relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    selected_power = db.relationship("Superpower", foreign_keys=[selected_power_id])
    attempts = db.relationship("MissionAttempt", back_populates="user", cascade="all, delete-orphan")
    achievements = db.relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_score = db.Column(db.Integer, nullable=False, default=0)
    level = db.Column(db.Integer, nullable=False, default=1)
    experience_points = db.Column(db.Integer, nullable=False, default=0)
    user = db.relationship("User", back_populates="profile")


class Superpower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    description = db.Column(db.String(240), nullable=False)
    effect = db.Column(db.String(240), nullable=False)
    icon = db.Column(db.String(32), nullable=False, default="spark")


class Mission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(280), nullable=False)
    difficulty = db.Column(db.String(16), nullable=False, default="Rookie")
    base_reward = db.Column(db.Integer, nullable=False, default=100)
    time_limit = db.Column(db.Integer, nullable=False, default=120)
    active = db.Column(db.Boolean, nullable=False, default=True)
    questions_json = db.Column(db.Text, nullable=False)
    attempts = db.relationship("MissionAttempt", back_populates="mission", cascade="all, delete-orphan")


class MissionAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("mission.id", ondelete="CASCADE"), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(16), nullable=False, default="started", index=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = db.Column(db.DateTime(timezone=True))
    correct_count = db.Column(db.Integer, nullable=False, default=0)
    power_name = db.Column(db.String(40))
    hint_used = db.Column(db.Boolean, nullable=False, default=False)
    user = db.relationship("User", back_populates="attempts")
    mission = db.relationship("Mission", back_populates="attempts")
    __table_args__ = (db.Index("ix_attempt_user_mission_status", "user_id", "mission_id", "status"),)


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(180), nullable=False)
    icon = db.Column(db.String(32), nullable=False, default="medal")
    criteria = db.Column(db.String(24), nullable=False)
    threshold = db.Column(db.Integer, nullable=False, default=1)


class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey("achievement.id", ondelete="CASCADE"), nullable=False)
    unlocked_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    user = db.relationship("User", back_populates="achievements")
    achievement = db.relationship("Achievement")
    __table_args__ = (db.UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))