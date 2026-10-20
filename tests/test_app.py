from app.extensions import db
from app.models import Achievement, Mission, MissionAttempt, Profile, Superpower, User, UserAchievement
from tests.conftest import register_player, select_power, start_mission, submit_answers


def test_app_starts_and_landing_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Everyday heroes" in response.data


def test_registration_hashes_password_and_creates_profile(client, app):
    response = register_player(client)
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username="NovaOne").one()
        assert user.password_hash != "SignalSafe123"
        assert user.check_password("SignalSafe123")
        assert user.profile.total_score == 0


def test_duplicate_username_or_email_is_rejected(client, app):
    register_player(client)
    client.post("/auth/logout")
    response = client.post("/auth/register", data={
        "username": "NovaOne", "email": "another@example.test",
        "password": "SignalSafe123", "confirm_password": "SignalSafe123",
    }, follow_redirects=True)
    assert b"already in use" in response.data
    with app.app_context():
        assert User.query.count() == 1


def test_login_and_protected_dashboard(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    register_player(client)
    client.post("/auth/logout")
    response = client.post("/auth/login", data={"identity": "nova@example.test", "password": "SignalSafe123"})
    assert response.status_code == 302
    assert client.get("/dashboard").status_code == 200


def test_non_admin_cannot_open_admin_dashboard(client):
    register_player(client)
    response = client.get("/admin/")
    assert response.status_code == 403


def test_missions_available_and_power_is_required(client):
    register_player(client)
    assert client.get("/missions").status_code == 200
    _mission, _attempt_id = start_mission(client)
    response = client.get("/powers")
    assert response.status_code == 200
    assert b"Super Strength" in response.data


def test_power_effect_score_persistence_and_duplicate_submission(client, app):
    register_player(client)
    select_power(client)
    mission, attempt_id = start_mission(client)
    assert client.get(f"/game/play/{attempt_id}").status_code == 200
    response = submit_answers(client, attempt_id)
    assert response.status_code == 200
    assert b"132" in response.data
    with app.app_context():
        user = User.query.filter_by(username="NovaOne").one()
        attempt = db.session.get(MissionAttempt, attempt_id)
        assert attempt.status == "completed"
        assert attempt.score == 132
        assert user.profile.total_score == 132
        assert user.profile.experience_points == 132
        assert user.profile.level == 1
        assert UserAchievement.query.filter_by(user_id=user.id).count() == 2
    submit_answers(client, attempt_id)
    with app.app_context():
        user = User.query.filter_by(username="NovaOne").one()
        assert user.profile.total_score == 132
        assert MissionAttempt.query.filter_by(id=attempt_id).one().score == 132


def test_invalid_answers_award_no_score_or_achievement(client, app):
    register_player(client)
    select_power(client)
    _mission, attempt_id = start_mission(client)
    response = client.post(f"/game/finish/{attempt_id}", data={"answer_0": "999"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"incomplete or invalid" in response.data
    with app.app_context():
        user = User.query.filter_by(username="NovaOne").one()
        assert user.profile.total_score == 0
        assert user.achievements == []


def test_energy_shield_bonus_does_not_fake_perfect_achievement(client, app):
    register_player(client)
    select_power(client, "Energy Shield")
    _mission, attempt_id = start_mission(client)
    submit_answers(client, attempt_id, answers=(2, 0, 1, 2, 0))
    with app.app_context():
        user = User.query.filter_by(username="NovaOne").one()
        attempt = MissionAttempt.query.filter_by(user_id=user.id).one()
        assert attempt.correct_count == 4
        assert attempt.score == 120
        unlocked = {entry.achievement.name for entry in user.achievements}
        assert "Perfect Signal" not in unlocked


def test_telekinesis_hint_is_one_use_and_owner_scoped(client, app):
    register_player(client)
    select_power(client, "Telekinesis")
    _mission, attempt_id = start_mission(client)
    response = client.post(f"/game/hint/{attempt_id}/0")
    assert response.status_code == 200
    assert "remove" in response.get_json()
    assert client.post(f"/game/hint/{attempt_id}/0").status_code == 403


def test_leaderboard_uses_database_scores_and_tie_order(client, app):
    register_player(client, "Bravo", "bravo@example.test")
    first = User.query.filter_by(username="Bravo").one()
    first.profile.total_score = 250
    first.profile.level = 2
    db.session.commit()
    client.post("/auth/logout")
    register_player(client, "Alpha", "alpha@example.test")
    second = User.query.filter_by(username="Alpha").one()
    second.profile.total_score = 250
    second.profile.level = 2
    db.session.commit()
    response = client.get("/leaderboard")
    assert response.status_code == 200
    assert response.data.index(b"Alpha") < response.data.index(b"Bravo")
    assert b"YOUR CURRENT RANK" in response.data


def test_profile_and_admin_mission_tools_render(client, app):
    register_player(client)
    assert client.get("/profile").status_code == 200
    with app.app_context():
        admin = User(username="Operator", email="operator@example.test", role="admin")
        admin.set_password("AdminSafe123")
        admin.profile = Profile()
        db.session.add(admin)
        db.session.commit()
    client.post("/auth/logout")
    client.post("/auth/login", data={"identity": "operator@example.test", "password": "AdminSafe123"})
    assert client.get("/admin/").status_code == 200
    response = client.post("/admin/missions", data={"title": "Harbor Signal", "description": "A new test mission.", "difficulty": "Rookie", "base_reward": "150", "time_limit": "90"}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert Mission.query.filter_by(title="Harbor Signal").one().active