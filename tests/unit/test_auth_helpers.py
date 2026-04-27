"""Unit tests for auth route helpers."""

from __future__ import annotations

from app.enums import Role
from app.routes import auth as auth_routes


def test_home_url_standard_user_targets_my_assets(app):
    with app.test_request_context("/"):
        url = auth_routes._home_url_for_role(Role.USER)
        assert "/my-assets" in url


def test_home_url_admin_targets_dashboard(app):
    with app.test_request_context("/"):
        url = auth_routes._home_url_for_role(Role.ADMIN)
        assert "/dashboard" in url
