from flask_wtf import FlaskForm


class EmptyForm(FlaskForm):
    """CSRF-only helper for POST actions outside dedicated WTForms views."""
