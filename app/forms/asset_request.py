from __future__ import annotations

from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

from app.forms._helpers import asset_type_choices, format_asset_type
from app.forms.base import StripWhitespaceForm


class AssetRequestCreateForm(StripWhitespaceForm):
    asset_type = SelectField(
        "Asset type",
        choices=[],
        coerce=format_asset_type,
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
        self.asset_type.choices = asset_type_choices()


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
