"""Unit tests for user route helpers."""

from __future__ import annotations

from app.enums import Department, Role
from app.extensions import db
from app.models import User
from app.routes import users as users_routes
from tests.conftest import cached_hash_password


def _seed_user(**kwargs) -> User:
    defaults = dict(
        username="u",
        email="u@example.com",
        password_hash=cached_hash_password("Pw1!aaaa"),
        role=Role.USER,
        department=Department.TECHNOLOGY,
    )
    defaults.update(kwargs)
    u = User(**defaults)
    db.session.add(u)
    db.session.commit()
    return u


def test_snapshot_user_returns_fields(app):
    with app.app_context():
        member = _seed_user(username="snap", email="snap@example.com")
        snap = users_routes._snapshot_user(member)
        assert snap["username"] == "snap"
        assert snap["role"] == Role.USER
        assert snap["department"] == Department.TECHNOLOGY


def test_build_user_update_audit_details_no_changes(app):
    with app.app_context():
        member = _seed_user(username="snap", email="snap@example.com")
        before = users_routes._snapshot_user(member)
        text = users_routes._build_user_update_audit_details(before, member)
        assert "no field changes" in text


def test_build_user_update_audit_details_each_change(app):
    with app.app_context():
        member = _seed_user(username="a", email="a@example.com")
        before = users_routes._snapshot_user(member)
        member.username = "b"
        member.role = Role.ADMIN
        member.department = Department.FINANCE
        text = users_routes._build_user_update_audit_details(before, member)
        assert "username" in text
        assert "role" in text
        assert "department" in text


def test_other_admin_counts_excluding_self(app):
    with app.app_context():
        _seed_user(username="adm1", email="adm1@example.com", role=Role.ADMIN)
        adm2 = _seed_user(username="adm2", email="adm2@example.com", role=Role.ADMIN)
        assert users_routes._other_admin_count(adm2.id) == 1


def test_filtered_users_bundle_filters(app):
    with app.app_context():
        _seed_user(
            username="finance_user",
            email="fu@example.com",
            department=Department.FINANCE,
        )
        _seed_user(
            username="alice_tech",
            email="at@example.com",
            department=Department.TECHNOLOGY,
        )

        rows, dk, rk, qs = users_routes._filtered_users_bundle(
            "TECHNOLOGY",
            "",
            "alice",
        )
        names = [u.username for u in rows]
        assert "alice_tech" in names
        assert "finance_user" not in names
        assert dk == "TECHNOLOGY"
        assert rk == ""
        assert qs == "alice"


def test_filtered_users_bundle_role_only(app):
    with app.app_context():
        _seed_user(username="only_admin", email="oa@example.com", role=Role.ADMIN)

        rows, dk, rk, qs = users_routes._filtered_users_bundle("", "ADMIN", "")
        assert all(u.role == Role.ADMIN for u in rows)
        assert rk == "ADMIN"
        assert dk == ""
