"""Unit tests for WTForms auth forms."""

from __future__ import annotations

import pytest

from app.forms.auth import RegistrationForm


def test_registration_password_requires_digit(app):
    with app.test_request_context(method="POST", path="/auth/register"):
        form = RegistrationForm(
            formdata=None,
            data={
                "username": "validuser",
                "email": "valid@example.com",
                "department": "TECHNOLOGY",
                "password": "NoDigits!Symbol",
                "confirm_password": "NoDigits!Symbol",
            },
        )
        assert form.validate() is False
        joined = " ".join(str(e) for e in form.password.errors).lower()
        assert "number" in joined


def test_registration_password_requires_symbol(app):
    with app.test_request_context(method="POST", path="/auth/register"):
        form = RegistrationForm(
            formdata=None,
            data={
                "username": "validuser",
                "email": "valid@example.com",
                "department": "TECHNOLOGY",
                "password": "HasDigits99",
                "confirm_password": "HasDigits99",
            },
        )
        assert form.validate() is False
        joined = " ".join(str(e) for e in form.password.errors).lower()
        assert "symbol" in joined


@pytest.mark.parametrize(
    "department_key",
    ["TECHNOLOGY", "FINANCE", "LEGAL"],
)
def test_registration_accepts_known_departments(app, department_key):
    with app.test_request_context(method="POST", path="/auth/register"):
        form = RegistrationForm(
            formdata=None,
            data={
                "username": "newperson",
                "email": "newperson@example.com",
                "department": department_key,
                "password": "GoodPass1!",
                "confirm_password": "GoodPass1!",
            },
        )
        assert form.validate() is True


def test_registration_rejects_unknown_department_key(app):
    with app.test_request_context(method="POST", path="/auth/register"):
        form = RegistrationForm(
            formdata=None,
            data={
                "username": "newperson",
                "email": "newperson@example.com",
                "department": "NOT_A_REAL_DEPT",
                "password": "GoodPass1!",
                "confirm_password": "GoodPass1!",
            },
        )
        assert form.validate() is False
