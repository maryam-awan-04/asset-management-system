"""Base form classes."""

from __future__ import annotations

from flask_wtf import FlaskForm


class StripWhitespaceForm(FlaskForm):
    """Strip leading/trailing whitespace from text fields before field validators run."""

    _STRIP_TYPES = frozenset({"StringField", "TextAreaField"})

    def validate(self, extra_validators=None):  # type: ignore[no-untyped-def]
        for field in self:
            if field.type in self._STRIP_TYPES and isinstance(field.data, str):
                field.data = field.data.strip()
        return super().validate(extra_validators=extra_validators)
