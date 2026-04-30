from __future__ import annotations

from datetime import date

from wtforms import DateField, RadioField, SubmitField, TextAreaField
from wtforms.validators import Length, Optional

from app.forms.base import StripWhitespaceForm

ASSET_NOTES_MAX_LEN = 4000


class AdminRequestReviewForm(StripWhitespaceForm):
    asset_id = RadioField("Asset", validators=[Optional()], coerce=int)
    return_due_date = DateField(
        "Return due date",
        validators=[Optional()],
        format="%Y-%m-%d",
        render_kw={"type": "date"},
    )
    asset_notes = TextAreaField(
        "Asset notes",
        validators=[Optional(), Length(max=ASSET_NOTES_MAX_LEN)],
        render_kw={
            "rows": 4,
            "maxlength": ASSET_NOTES_MAX_LEN,
            "id": "admin-approve-asset-notes",
        },
    )
    approve = SubmitField("Approve and Assign")
    reject = SubmitField("Reject request")

    def __init__(
        self,
        *args,
        asset_radio_choices: list[tuple[str, str]],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.asset_id.choices = asset_radio_choices

    def validate(self, extra_validators=None):  # type: ignore[no-untyped-def]
        ok = super().validate(extra_validators=extra_validators)
        if self.approve.data:
            if self.asset_id.choices and self.asset_id.data is None:
                self.asset_id.errors.append(
                    "Select an available asset before approving.",
                )
                ok = False
            if self.return_due_date.data is not None:
                if self.return_due_date.data < date.today():
                    self.return_due_date.errors.append(
                        "Return due date cannot be before today.",
                    )
                    ok = False
        return ok
