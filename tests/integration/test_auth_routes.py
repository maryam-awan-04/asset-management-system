"""Integration tests for auth blueprint."""

from __future__ import annotations

from sqlalchemy import func, select

from app.enums import AuditAction
from app.extensions import db
from app.models import AuditLog, User


def test_login_get_returns_200(client):
    rv = client.get("/auth/login")
    assert rv.status_code == 200


def test_register_get_returns_200(client):
    rv = client.get("/auth/register")
    assert rv.status_code == 200


def test_login_success_redirects_user_to_my_assets(client, credentials_user):
    rv = client.post(
        "/auth/login",
        data={
            "username": credentials_user["username"],
            "password": credentials_user["password"],
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert "/my-assets" in rv.headers["Location"]


def test_login_success_redirects_admin_to_dashboard(client, credentials_admin):
    rv = client.post(
        "/auth/login",
        data={
            "username": credentials_admin["username"],
            "password": credentials_admin["password"],
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert "/dashboard" in rv.headers["Location"]


def test_login_bad_password_returns_200_and_no_session(client, credentials_user):
    rv = client.post(
        "/auth/login",
        data={
            "username": credentials_user["username"],
            "password": "WrongPass9!",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200


def test_login_unknown_user_returns_200(client):
    rv = client.post(
        "/auth/login",
        data={"username": "nobody_here", "password": "Whatever1!"},
        follow_redirects=False,
    )
    assert rv.status_code == 200


def test_login_respects_safe_next_parameter(client, credentials_user):
    rv = client.post(
        "/auth/login?next=/assets/",
        data={
            "username": credentials_user["username"],
            "password": credentials_user["password"],
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert rv.headers["Location"].endswith("/assets/")


def test_register_success_creates_user_and_redirects(client, app):
    rv = client.post(
        "/auth/register",
        data={
            "username": "brandnew",
            "email": "brandnew@example.com",
            "department": "HR",
            "password": "Register1!X",
            "confirm_password": "Register1!X",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert "/auth/login" in rv.headers["Location"]

    with app.app_context():
        user = db.session.scalar(select(User).filter_by(username="brandnew"))
        assert user is not None
        assert user.email == "brandnew@example.com"


def test_register_duplicate_username_rejected(client, credentials_user):
    rv = client.post(
        "/auth/register",
        data={
            "username": credentials_user["username"],
            "email": "other@example.com",
            "department": "LEGAL",
            "password": "Register1!X",
            "confirm_password": "Register1!X",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200


def test_logout_requires_login(client):
    rv = client.post("/auth/logout", follow_redirects=False)
    assert rv.status_code == 302


def test_logout_when_logged_in_redirects_to_login(client, credentials_user):
    client.post(
        "/auth/login",
        data={
            "username": credentials_user["username"],
            "password": credentials_user["password"],
        },
    )
    rv = client.post("/auth/logout", follow_redirects=False)
    assert rv.status_code == 302
    assert "/auth/login" in rv.headers["Location"]


def test_login_success_writes_audit_row(app, client, credentials_user):
    with app.app_context():
        before = db.session.scalar(select(func.count(AuditLog.id)))

    client.post(
        "/auth/login",
        data={
            "username": credentials_user["username"],
            "password": credentials_user["password"],
        },
    )

    with app.app_context():
        after = db.session.scalar(select(func.count(AuditLog.id)))
        last = db.session.scalar(
            select(AuditLog).order_by(AuditLog.id.desc()).limit(1),
        )
        assert after > before
        assert last is not None
        assert last.action == AuditAction.LOGIN_SUCCESS
