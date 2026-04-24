from __future__ import annotations

from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import (
    DateField,
    Field,
    HiddenField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from app.enums import AssetType, Status
from app.extensions import db
from app.models import Asset, User


def _asset_type_choices() -> list[tuple[str, str]]:
    return [(t.name, t.value) for t in AssetType]


def _status_choices() -> list[tuple[str, str]]:
    return [(s.name, s.value) for s in Status]


def _format_asset_type(key: str | None) -> AssetType | None:
    if key is None or key == "":
        return None
    try:
        return AssetType[key]
    except KeyError as exc:
        raise ValidationError("Invalid asset type.") from exc


def _format_status(key: str | None) -> Status | None:
    if key is None or key == "":
        return None
    try:
        return Status[key]
    except KeyError as exc:
        raise ValidationError("Invalid status.") from exc


class AssetCreateForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[
            DataRequired(message="Name is required."),
            Length(max=200, message="Name cannot exceed 200 characters."),
        ],
    )
    serial_number = StringField(
        "Serial number",
        validators=[
            DataRequired(message="Serial number is required."),
            Length(max=128, message="Serial number cannot exceed 128 characters."),
        ],
    )
    asset_type = SelectField(
        "Asset type",
        choices=[],
        coerce=_format_asset_type,
        validators=[DataRequired(message="Choose an asset type.")],
    )
    status = SelectField(
        "Status",
        choices=[],
        coerce=_format_status,
        validators=[DataRequired(message="Choose a status.")],
    )
    purchase_date = DateField(
        "Purchase date",
        validators=[Optional()],
        format="%Y-%m-%d",
        render_kw={"type": "date"},
    )
    expiry_date = DateField(
        "Expiry date",
        validators=[Optional()],
        format="%Y-%m-%d",
        render_kw={"type": "date"},
    )
    notes = TextAreaField(
        "Notes",
        validators=[Optional(), Length(max=4000)],
        render_kw={"rows": 3},
    )
    submit = SubmitField("Create")

    def __init__(self, *args, **kwargs):
        self._exclude_asset_id: int | None = kwargs.pop("exclude_asset_id", None)
        super().__init__(*args, **kwargs)
        self.asset_type.choices = [
            ("", "-- Select asset type --"),
            *_asset_type_choices(),
        ]
        self.status.choices = [
            ("", "-- Select status --"),
            *_status_choices(),
        ]

    def validate_serial_number(self, field: Field) -> None:
        sn = (field.data or "").strip()
        if not sn:
            return
        stmt = select(Asset.id).where(Asset.serial_number == sn).limit(1)
        if self._exclude_asset_id is not None:
            stmt = stmt.where(Asset.id != self._exclude_asset_id)
        existing = db.session.scalar(stmt)
        if existing is not None:
            raise ValidationError("An asset with this serial number already exists.")


class AssetEditForm(AssetCreateForm):
    submit = SubmitField("Save changes")
    assign_user_id = HiddenField(validators=[Optional()])

    def __init__(self, *args, asset_id: int, **kwargs):
        super().__init__(*args, exclude_asset_id=asset_id, **kwargs)
        self.asset_type.choices = _asset_type_choices()
        self.status.choices = _status_choices()

    def validate(self, extra_validators=None):  # type: ignore[no-untyped-def]
        result = super().validate(extra_validators=extra_validators)
        if self.status.data == Status.ASSIGNED:
            raw = (self.assign_user_id.data or "").strip()
            if not raw.isdigit():
                self.assign_user_id.errors.append(
                    "Search and select a user when status is Assigned.",
                )
                result = False
            else:
                uid = int(raw)
                user = db.session.get(User, uid)
                if user is None:
                    self.assign_user_id.errors.append("Selected user was not found.")
                    result = False
        return result
