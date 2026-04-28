"""Shared pytest fixtures and test utilities."""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache

import pytest
from werkzeug.test import TestResponse

from app import create_app
from app.enums import Department, Role
from app.extensions import db
from app.models import User
from app.passwords import hash_password as _hash_password
from app.seed.constants import PYTEST_FIXTURE_PASSWORD


@lru_cache(maxsize=64)
def cached_hash_password(plain_password: str) -> str:
    return _hash_password(plain_password)


def assert_redirect(
    response,
    *,
    location_contains: str,
    status_code: int = 302,
) -> None:
    assert response.status_code == status_code
    loc = response.headers.get("Location", "")
    assert location_contains in loc


def login(
    client,
    *,
    username: str,
    password: str,
    login_path: str = "/auth/login",
) -> TestResponse:
    return client.post(
        login_path,
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def login_as(
    client,
    creds: Mapping[str, str],
    *,
    login_path: str = "/auth/login",
) -> TestResponse:
    return login(
        client,
        username=creds["username"],
        password=creds["password"],
        login_path=login_path,
    )


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
            password_hash=cached_hash_password(password_plain),
            role=role,
            department=department,
        ),
    )
    db.session.commit()


@pytest.fixture
def plain_password() -> str:
    return PYTEST_FIXTURE_PASSWORD


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
