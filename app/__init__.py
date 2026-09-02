from pathlib import Path
from datetime import timedelta
import os
import secrets

from flask import Flask, send_from_directory
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from sqlalchemy import text

db = SQLAlchemy()
login_manager = LoginManager()
oauth = OAuth()


def ensure_user_profile_columns():
    # Existing local installations used SQLite before learner-profile fields
    # were added. Managed production databases are created from the models.
    if db.engine.dialect.name != "sqlite":
        return

    columns = {
        row["name"]
        for row in db.session.execute(text("PRAGMA table_info(user)")).mappings()
    }
    required_columns = {
        "learning_status": "VARCHAR(80)",
        "learning_level": "VARCHAR(80)",
        "learning_goal": "VARCHAR(300)",
        "skills": "VARCHAR(500)",
    }

    for column_name, column_type in required_columns.items():
        if column_name not in columns:
            db.session.execute(
                text(f"ALTER TABLE user ADD COLUMN {column_name} {column_type}")
            )

    db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    from app.models import User

    return db.session.get(User, int(user_id))


def create_app(test_config=None):
    load_dotenv()
    project_root = Path(__file__).resolve().parent.parent
    frontend_dist = project_root / "frontend" / "dist"
    app = Flask(__name__, static_folder=str(frontend_dist), static_url_path="")

    database_path = project_root / "coursewise.db"
    database_url = os.environ.get("DATABASE_URL", "").strip()

    # Some managed services still provide the older postgres:// scheme.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SECRET_KEY"] = os.environ.get("COURSEWISE_SECRET_KEY")
    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = secrets.token_urlsafe(32)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        database_url or f"sqlite:///{database_path}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    oauth.init_app(app)

    google_client_id = os.environ.get("GOOGLE_CLIENT_ID")
    google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if google_client_id and google_client_secret:
        oauth.register(
            name="google",
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url=(
                "https://accounts.google.com/.well-known/openid-configuration"
            ),
            client_kwargs={"scope": "openid email profile"},
        )

    with app.app_context():
        from app import models
        db.create_all()
        ensure_user_profile_columns()

    from app.routes.auth import auth_bp
    from app.routes.api import api_bp
    from app.routes.interactions import interactions_bp
    from app.routes.main import main_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(interactions_bp)
    app.register_blueprint(main_bp)

    @app.get("/")
    @app.get("/<path:requested_path>")
    def serve_react_app(requested_path=""):
        """Serve the built React dashboard when Coursewise runs in the cloud."""
        if not frontend_dist.exists():
            return (
                "The React dashboard has not been built yet. Run npm run build "
                "inside the frontend folder.",
                503,
            )

        requested_file = frontend_dist / requested_path
        if requested_path and requested_file.is_file():
            return send_from_directory(frontend_dist, requested_path)

        return send_from_directory(frontend_dist, "index.html")

    return app
