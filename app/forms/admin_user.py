from __future__ import annotations

from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import Field, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError

from app.enums import Department, Role
from app.extensions import db
from app.models import User


def _role_choices() -> list[tuple[str, str]]:
    return [(r.name, r.value) for r in Role]


def _department_choices() -> list[tuple[str, str]]:
    return [(d.name, d.value) for d in Department]


def _format_role(key: str | None) -> Role | None:
    if key is None or key == "":
        return None
    try:
        return Role[key]
    except KeyError as exc:
        raise ValidationError("Invalid role.") from exc


def _format_department(key: str | None) -> Department | None:
    if key is None or key == "":
        return None
    try:
        return Department[key]
    except KeyError as exc:
        raise ValidationError("Invalid department.") from exc


class AdminUserEditForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(
                min=3, max=80, message="Username must be between 3 and 80 characters."
            ),
        ],
    )
    role = SelectField(
        "Role",
        choices=[],
        coerce=_format_role,
        validators=[DataRequired(message="Choose a role.")],
    )
    department = SelectField(
        "Department",
        choices=[],
        coerce=_format_department,
        validators=[DataRequired(message="Choose a department.")],
    )
    submit = SubmitField("Save changes")

    def __init__(self, *args, exclude_user_id: int, **kwargs):
        self._exclude_user_id = exclude_user_id
        super().__init__(*args, **kwargs)
        self.role.choices = _role_choices()
        self.department.choices = _department_choices()

    def validate_username(self, field: Field) -> None:
        name = (field.data or "").strip()
        if not name:
            return
        stmt = select(User.id).where(User.username == name).limit(1)
        stmt = stmt.where(User.id != self._exclude_user_id)
        if db.session.scalar(stmt) is not None:
            raise ValidationError("That username is already taken.")
