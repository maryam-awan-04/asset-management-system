"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from app import create_app
from app.enums import Department, Role
from app.extensions import db
from app.models import User
from app.passwords import hash_password


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _make_user(
    *,
    username: str,
    email: str,
    password_plain: str,
    role: Role = Role.USER,
    department: Department = Department.TECHNOLOGY,
) -> None:
    db.session.add(
        User(
            username=username,
            email=email,
            password_hash=hash_password(password_plain),
            role=role,
            department=department,
        ),
    )
    db.session.commit()


@pytest.fixture
def plain_password() -> str:
    return "Valid1!Password"


@pytest.fixture
def credentials_user(app, plain_password):
    with app.app_context():
        _make_user(
            username="alice",
            email="alice@example.com",
            password_plain=plain_password,
        )
    return {"username": "alice", "password": plain_password}


@pytest.fixture
def credentials_admin(app, plain_password):
    with app.app_context():
        _make_user(
            username="adminbob",
            email="adminbob@example.com",
            password_plain=plain_password,
            role=Role.ADMIN,
        )
    return {"username": "adminbob", "password": plain_password}
