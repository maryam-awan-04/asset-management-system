from __future__ import annotations

from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError

from app.enums import AssetType
from app.forms.base import StripWhitespaceForm


def _asset_type_choices() -> list[tuple[str, str]]:
    return [(t.name, t.value) for t in AssetType]


def _format_asset_type(key: str | None) -> AssetType | None:
    if key is None or key == "":
        return None
    try:
        return AssetType[key]
    except KeyError as exc:
        raise ValidationError("Invalid asset type.") from exc


class AssetRequestCreateForm(StripWhitespaceForm):
    asset_type = SelectField(
        "Asset type",
        choices=[],
        coerce=_format_asset_type,
        validators=[DataRequired(message="Choose an asset type.")],
    )
    note = TextAreaField(
        "Note",
        validators=[
            DataRequired(message="Please include a note for this request."),
            Length(
                min=5,
                max=1000,
                message="Note must be between 5 and 1000 characters.",
            ),
        ],
        render_kw={
            "rows": 4,
            "placeholder": "Explain what you need and why (team, project, urgency, etc.).",
        },
    )
    submit = SubmitField("Submit Request")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.asset_type.choices = _asset_type_choices()


class AssetRequestEditNoteForm(StripWhitespaceForm):
    note = TextAreaField(
        "Note",
        validators=[
            DataRequired(message="Please include a note for this request."),
            Length(
                min=5,
                max=1000,
                message="Note must be between 5 and 1000 characters.",
            ),
        ],
        render_kw={
            "rows": 4,
            "placeholder": "Explain what you need and why (team, project, urgency, etc.).",
        },
    )
    submit = SubmitField("Save Note")
