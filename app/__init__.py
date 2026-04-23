from __future__ import annotations

import os
from typing import Optional

from flask import Flask

from app.config import get_config
from app.extensions import csrf, db, login_manager


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

    # Set to a real login route when auth blueprint is registered
    login_manager.login_view = None

    @login_manager.user_loader
    def load_user(user_id: str):
        from app import models

        User = getattr(models, "User", None)
        if User is None:
            return None
        return db.session.get(User, int(user_id))

    from app import models as _models  # noqa: F401
    from app.routes import main as main_routes

    app.register_blueprint(main_routes.bp)

    with app.app_context():
        db.create_all()

    return app
