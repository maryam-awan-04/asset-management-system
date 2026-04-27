"""Main blueprint: dashboard, admin request review, user portal, health."""

from app.routes.main import admin_requests as _admin_requests  # noqa: F401
from app.routes.main import core as _core  # noqa: F401
from app.routes.main import user_portal as _user_portal  # noqa: F401
from app.routes.main.blueprint import bp

__all__ = ["bp"]
