import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "test-secret",
    })
    with application.app_context():
        db.drop_all()
        db.create_all()
        from app import seed_content
        seed_content()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register_player(client, username="NovaOne", email="nova@example.test"):
    return client.post("/auth/register", data={
        "username": username,
        "email": email,
        "password": "SignalSafe123",
        "confirm_password": "SignalSafe123",
    }, follow_redirects=True)


def select_power(client, name="Super Strength"):
    from app.models import Superpower
    power = Superpower.query.filter_by(name=name).first()
    return client.post("/powers", data={"power_id": power.id}, follow_redirects=True)


def start_mission(client):
    from app.models import Mission
    mission = Mission.query.filter_by(title="Neon Harbor Evacuation").first()
    response = client.post(f"/game/start/{mission.id}", follow_redirects=False)
    attempt_id = int(response.headers["Location"].rsplit("/", 1)[1])
    return mission, attempt_id


def submit_answers(client, attempt_id, answers=(2, 2, 1, 2, 0)):
    data = {f"answer_{index}": str(answer) for index, answer in enumerate(answers)}
    return client.post(f"/game/finish/{attempt_id}", data=data, follow_redirects=True)