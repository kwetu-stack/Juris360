import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    load_dotenv()
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///data/juris360.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOADS_DIR"] = os.environ.get("UPLOADS_DIR", "data/uploads")
    os.makedirs(app.config["UPLOADS_DIR"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Create tables and seed admin if needed
    from . import models  # noqa
    with app.app_context():
        db.create_all()
        from .models import User
        admin_user = os.environ.get("ADMIN_USER", "admin")
        admin_pass = os.environ.get("ADMIN_PASS", "kwetutech00")
        if not User.query.filter_by(username=admin_user).first():
            db.session.add(User(username=admin_user, password=admin_pass))
            db.session.commit()

        # --- Auto-seed demo data (guarded by env flag) ---
        # Runs only if AUTO_SEED=true and there are no clients yet.
        if os.getenv("AUTO_SEED", "false").lower() == "true":
            try:
                from .models import Client
                if Client.query.count() == 0:
                    from .seed import run_seed  # factor your seed_demo.py into app/seed.py
                    run_seed()
            except Exception as e:
                # Keep startup resilient; log to console but don't crash the app.
                print(f"[AUTO_SEED] Skipped due to error: {e}")

    # Register blueprints
    from .blueprints.auth import bp as auth_bp
    from .blueprints.core import bp as core_bp
    from .blueprints.clients import bp as clients_bp
    from .blueprints.cases import bp as cases_bp
    from .blueprints.documents import bp as documents_bp
    from .blueprints.billing import bp as billing_bp
    from .blueprints.schedule import bp as schedule_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(core_bp)
    app.register_blueprint(clients_bp, url_prefix="/clients")
    app.register_blueprint(cases_bp, url_prefix="/cases")
    app.register_blueprint(documents_bp, url_prefix="/documents")
    app.register_blueprint(billing_bp, url_prefix="/billing")
    app.register_blueprint(schedule_bp, url_prefix="/schedule")
    return app
