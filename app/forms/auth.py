from __future__ import annotations

import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.enums import Department


def _password_has_digit(form: FlaskForm, field: PasswordField) -> None:
    if field.data and not re.search(r"\d", field.data):
        raise ValidationError("Password must contain at least one number.")


def _password_has_symbol(form: FlaskForm, field: PasswordField) -> None:
    if field.data and not re.search(r"[^\w\s]", field.data):
        raise ValidationError(
            "Password must contain at least one symbol (e.g. !, @, #, $)."
        )


def _department_choices() -> list[tuple[str, str]]:
    return [(d.name, d.value) for d in Department]


def _format_department(key: str | None) -> Department | None:
    if key is None or key == "":
        return None
    try:
        return Department[key]
    except KeyError as exc:
        raise ValidationError("Invalid department.") from exc


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(message="Username is required."), Length(max=80)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required.")],
    )
    remember_me = BooleanField("Stay signed in")
    submit = SubmitField("Sign in")


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(
                min=3, max=80, message="Username must be between 3 and 80 characters."
            ),
        ],
    )
    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email(message="Enter a valid email address."),
            Length(max=255),
        ],
    )
    department = SelectField(
        "Department",
        choices=[],
        coerce=_format_department,
        validators=[DataRequired(message="Choose a department.")],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, message="Password must be at least 8 characters."),
            _password_has_digit,
            _password_has_symbol,
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Create account")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.department.choices = [
            ("", "-- Select department --"),
            *_department_choices(),
        ]
