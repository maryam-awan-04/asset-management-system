from __future__ import annotations

import os
from typing import Optional

from flask import Flask

from app.config import ProductionConfig, get_config, validate_production_config
from app.extensions import csrf, db, limiter, login_manager
from app.forms.empty import EmptyForm


def _normalize_database_url(uri: str) -> str:
    if uri.startswith("postgres://"):
        return uri.replace("postgres://", "postgresql://", 1)
    return uri


def create_app(config_name: Optional[str] = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    config_class = get_config(config_name)
    app.config.from_object(config_class)

    if config_class is ProductionConfig:
        validate_production_config(app.config.get("SECRET_KEY"))

    os.makedirs(app.instance_path, exist_ok=True)
    if not app.config.get("TESTING"):
        explicit_uri = os.environ.get("SQLALCHEMY_DATABASE_URI") or os.environ.get(
            "DATABASE_URL",
        )
        if explicit_uri:
            app.config["SQLALCHEMY_DATABASE_URI"] = _normalize_database_url(
                explicit_uri.strip(),
            )
        else:
            db_path = os.path.join(app.instance_path, "app.db")
            app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.models import User

        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_logout_form():
        return {"logout_form": EmptyForm()}

    @app.context_processor
    def inject_enums_for_templates():
        from app.enums import AssetType, Department, RequestStatus, Role, Status

        return {
            "AssetType": AssetType,
            "Department": Department,
            "RequestStatus": RequestStatus,
            "Role": Role,
            "Status": Status,
        }

    from app import models as _models  # noqa: F401
    from app.routes import assets as assets_routes
    from app.routes import auth as auth_routes
    from app.routes import users as users_routes
    from app.routes.main import bp as main_bp

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(assets_routes.bp)
    app.register_blueprint(users_routes.bp)

    with app.app_context():
        db.create_all()
        if app.config.get("DEBUG"):
            from app.seed import ensure_demo_assets, ensure_localdev_admin

            ensure_localdev_admin()
            ensure_demo_assets()

    return app
