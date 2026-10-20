import os

import click
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_wtf.csrf import CSRFError

from app.extensions import csrf, db, login_manager


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User
    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.game import bp as game_bp
    from app.admin import bp as admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(game_bp, url_prefix="/game")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.template_filter("fromjson")
    def fromjson_filter(value):
        import json
        return json.loads(value)

    @app.cli.command("init-db")
    def init_db_command():
        db.create_all()
        click.echo("Database tables are ready.")

    @app.cli.command("seed")
    def seed_command():
        db.create_all()
        seed_content()
        click.echo("SuperQuest content is ready.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option()
    def create_admin_command(username, email, password):
        from app.models import Profile, User
        if User.query.filter_by(role="admin").first():
            raise click.ClickException("An administrator already exists.")
        if User.query.filter(db.or_(User.username == username, User.email == email.lower())).first():
            raise click.ClickException("That username or email is already registered.")
        user = User(username=username, email=email.lower(), role="admin")
        user.set_password(password)
        user.profile = Profile()
        db.session.add(user)
        db.session.commit()
        click.echo(f"Administrator {username} created.")

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/error.html", title="Access denied", message="That area is reserved for authorized heroes."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/error.html", title="Signal lost", message="This page is not on our mission map."), 404

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("errors/error.html", title="Systems offline", message="Something went wrong. Please try again."), 500

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        return render_template("errors/error.html", title="Form expired", message="Refresh the page and submit the form again."), 400

    with app.app_context():
        db.create_all()
        if app.config.get("SEED_DEFAULTS", True):
            seed_content()
    return app


def seed_content():
    import json
    from app.models import Achievement, Mission, Superpower

    powers = [
        ("Super Strength", "Move the impossible. Your raw power turns close calls into stronger scores.", "Earn a 10% score boost on every mission.", "strength"),
        ("Velocity", "Think fast and move faster. Finish with time to spare for a speed bonus.", "Earn up to 20 bonus points for quick, accurate runs.", "speed"),
        ("Energy Shield", "Stay in the fight. Your shield absorbs one mistake on each mission.", "One incorrect answer is forgiven when calculating your result.", "shield"),
        ("Telekinesis", "Read the field from every angle. A tactical hint is available during play.", "Unlock one hint that removes a wrong choice from a question.", "telekinesis"),
        ("Elemental Control", "Channel the elements with precision. Perfect runs ignite a score bonus.", "Earn a 15% bonus for a flawless mission.", "element"),
    ]
    questions = [
        {"prompt": "A rescue beacon flashes three times every 12 seconds. How many flashes in one minute?", "choices": ["12", "15", "18", "24"], "answer": 2},
        {"prompt": "A bridge has 40 support panels. A storm damages one quarter. How many remain intact?", "choices": ["10", "20", "30", "35"], "answer": 2},
        {"prompt": "The team leaves at 14:35 and travels for 45 minutes. When do they arrive?", "choices": ["15:10", "15:20", "15:30", "16:20"], "answer": 1},
        {"prompt": "Three drones each carry 8 supply packs. How many packs reach the shelter?", "choices": ["11", "18", "24", "32"], "answer": 2},
        {"prompt": "A safe route is 2 km east, then 2 km north. Which direction is the final leg?", "choices": ["North", "South", "East", "West"], "answer": 0},
    ]
    for name, description, effect, icon in powers:
        if not Superpower.query.filter_by(name=name).first():
            db.session.add(Superpower(name=name, description=description, effect=effect, icon=icon))
    mission_specs = [
        ("Neon Harbor Evacuation", "Coordinate a fast rescue across a storm-lit harbor. Read the signals, secure the route, and get every civilian to safety.", "Rookie", 120, 150),
        ("Skyline Blackout", "Restore power to the city grid before the skyline goes dark.", "Veteran", 180, 120),
        ("Crystal Core", "Stabilize an unstable energy core beneath the observatory.", "Elite", 240, 105),
    ]
    for title, description, difficulty, reward, time_limit in mission_specs:
        if not Mission.query.filter_by(title=title).first():
            db.session.add(Mission(title=title, description=description, difficulty=difficulty, base_reward=reward, time_limit=time_limit, questions_json=json.dumps(questions)))
    achievement_specs = [
        ("First Flight", "Complete your first mission.", "first", 1),
        ("City Guardian", "Complete five missions.", "missions", 5),
        ("Bright Spark", "Earn 300 total score.", "score", 300),
        ("Perfect Signal", "Answer every question correctly in one mission.", "perfect", 1),
    ]
    for name, description, criteria, threshold in achievement_specs:
        if not Achievement.query.filter_by(name=name).first():
            db.session.add(Achievement(name=name, description=description, criteria=criteria, threshold=threshold))
    db.session.commit()