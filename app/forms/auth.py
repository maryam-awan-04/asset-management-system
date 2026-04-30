from __future__ import annotations

import re

from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.forms._helpers import department_choices, format_department
from app.forms.base import StripWhitespaceForm


def _password_has_digit(form: StripWhitespaceForm, field: PasswordField) -> None:
    if field.data and not re.search(r"\d", field.data):
        raise ValidationError("Password must contain at least one number.")


def _password_has_symbol(form: StripWhitespaceForm, field: PasswordField) -> None:
    if field.data and not re.search(r"[^\w\s]", field.data):
        raise ValidationError(
            "Password must contain at least one symbol (e.g. !, @, #, $)."
        )


class LoginForm(StripWhitespaceForm):
    username = StringField(
        "Username",
        validators=[DataRequired(message="Username is required."), Length(max=80)],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(max=128, message="Password cannot exceed 128 characters."),
        ],
    )
    remember_me = BooleanField("Stay signed in")
    submit = SubmitField("Sign in")


class RegistrationForm(StripWhitespaceForm):
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
        coerce=format_department,
        validators=[DataRequired(message="Choose a department.")],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(
                min=8,
                max=128,
                message="Password must be between 8 and 128 characters.",
            ),
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
            *department_choices(),
        ]
