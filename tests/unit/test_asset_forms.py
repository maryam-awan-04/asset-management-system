"""Unit tests for WTForms asset forms."""

from __future__ import annotations

from datetime import date

from werkzeug.datastructures import MultiDict

from app.enums import AssetType, Status
from app.extensions import db
from app.forms.asset import AssetCreateForm, AssetEditForm
from app.models import Asset


def _create_asset_for_form() -> int:
    asset = Asset(
        name="Form Seed Asset",
        serial_number="FORM-SEED-001",
        asset_type=AssetType.LAPTOP,
        status=Status.AVAILABLE,
        purchase_date=date(2024, 1, 1),
        expiry_date=None,
        notes=None,
    )
    db.session.add(asset)
    db.session.commit()
    return asset.id


def test_asset_create_form_rejects_assigned_status(app):
    with app.test_request_context(method="POST", path="/assets/new"):
        form = AssetCreateForm(
            formdata=None,
            data={
                "name": "Laptop A",
                "serial_number": "SN-NEW-1",
                "asset_type": "LAPTOP",
                "status": "ASSIGNED",
                "purchase_date": "2024-03-01",
                "expiry_date": "",
                "notes": "",
            },
        )
        assert form.validate() is False
        joined = " ".join(form.status.errors).lower()
        assert "cannot be created as assigned" in joined


def test_asset_edit_form_requires_assign_user_when_assigned(app):
    with app.app_context():
        asset_id = _create_asset_for_form()

    with app.test_request_context(method="POST", path=f"/assets/{asset_id}/edit"):
        form = AssetEditForm(
            asset_id=asset_id,
            formdata=MultiDict(
                {
                    "name": "Form Seed Asset",
                    "serial_number": "FORM-SEED-001",
                    "asset_type": "LAPTOP",
                    "status": "ASSIGNED",
                    "assign_user_id": "",
                    "assignment_return_due": "",
                    "returned_on": "",
                },
            ),
        )
        assert form.validate() is False
        joined = " ".join(form.assign_user_id.errors).lower()
        assert "search and select a user" in joined


def test_asset_edit_form_rejects_returned_when_no_open_assignment(app):
    with app.app_context():
        asset_id = _create_asset_for_form()

    with app.test_request_context(method="POST", path=f"/assets/{asset_id}/edit"):
        form = AssetEditForm(
            asset_id=asset_id,
            formdata=MultiDict(
                {
                    "name": "Form Seed Asset",
                    "serial_number": "FORM-SEED-001",
                    "asset_type": "LAPTOP",
                    "status": "RETURNED",
                    "assign_user_id": "",
                    "assignment_return_due": "",
                    "returned_on": date.today().isoformat(),
                },
            ),
        )
        assert form.validate() is False
        joined = " ".join(form.status.errors).lower()
        assert "requires an active assignment" in joined
