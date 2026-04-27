from __future__ import annotations

import os
from typing import Optional

from flask import Flask

from app.config import get_config
from app.extensions import csrf, db, limiter, login_manager
from app.forms.empty import EmptyForm


def create_app(config_name: Optional[str] = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    config_class = get_config(config_name)
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)
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
