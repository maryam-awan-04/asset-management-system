from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
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
from app.forms.base import StripWhitespaceForm
from app.models import Asset, Assignment, User

ASSET_NOTES_MAX_LEN = 4000


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


def _status_choices_for_create() -> list[tuple[str, str]]:
    """Statuses that can be chosen when creating a new asset (not Assigned/Returned)."""
    skip = {Status.ASSIGNED, Status.RETURNED}
    return [(s.name, s.value) for s in Status if s not in skip]


class AssetCreateForm(StripWhitespaceForm):
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
            *_status_choices_for_create(),
        ]

    def validate_status(self, field: Field) -> None:
        if field.data == Status.ASSIGNED:
            raise ValidationError(
                "New assets cannot be created as Assigned. Create the asset first, then edit it to assign.",
            )
        if field.data == Status.RETURNED:
            raise ValidationError(
                "New assets cannot be created as Returned.",
            )

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
    assignment_return_due = DateField(
        "Return date (optional)",
        validators=[Optional()],
        format="%Y-%m-%d",
        render_kw={"type": "date"},
    )
    returned_on = DateField(
        "Return date",
        validators=[Optional()],
        format="%Y-%m-%d",
        render_kw={"type": "date"},
    )

    def __init__(self, *args, asset_id: int, **kwargs):
        self._asset_id = asset_id
        super().__init__(*args, exclude_asset_id=asset_id, **kwargs)
        self.asset_type.choices = _asset_type_choices()
        self.status.choices = _status_choices()

    def validate_status(self, field: Field) -> None:
        pass

    def validate(self, extra_validators=None):  # type: ignore[no-untyped-def]
        result = super().validate(extra_validators=extra_validators)
        if (
            self.assignment_return_due.data is not None
            and self.assignment_return_due.data < date.today()
        ):
            self.assignment_return_due.errors.append(
                "Return date cannot be before today.",
            )
            result = False
        if self.status.data == Status.RETURNED:
            if self.returned_on.data is None:
                self.returned_on.errors.append(
                    "Return date is required.",
                )
                result = False
            else:
                open_n = (
                    db.session.scalar(
                        select(func.count(Assignment.id)).where(
                            Assignment.asset_id == self._asset_id,
                            Assignment.returned_date.is_(None),
                        ),
                    )
                    or 0
                )
                if open_n == 0:
                    self.status.errors.append(
                        "Returned status requires an active assignment. "
                    )
                    result = False
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
