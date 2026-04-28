"""Unit tests for main blueprint helpers."""

from __future__ import annotations

from app.enums import AssetType, Department, RequestStatus, Role, Status
from app.extensions import db
from app.forms.empty import EmptyForm
from app.models import Asset, AssetRequest, User
from app.routes.main import admin_requests as admin_requests_module
from tests.conftest import cached_hash_password


def test_admin_request_review_template_kwargs(app):
    with app.app_context():
        requester = User(
            username="main_kw_user",
            email="main_kw@example.com",
            password_hash=cached_hash_password("Pw1!aaaa"),
            role=Role.USER,
            department=Department.TECHNOLOGY,
        )
        db.session.add(requester)
        db.session.flush()
        req = AssetRequest(
            user_id=requester.id,
            asset_type=AssetType.LAPTOP,
            status=RequestStatus.PENDING,
            note="n",
        )
        db.session.add(req)
        a1 = Asset(
            name="A1",
            serial_number="SN-MAIN-1",
            asset_type=AssetType.LAPTOP,
            status=Status.AVAILABLE,
            purchase_date=None,
            expiry_date=None,
            notes="  trimmed  ",
        )
        a2 = Asset(
            name="A2",
            serial_number="SN-MAIN-2",
            asset_type=AssetType.LAPTOP,
            status=Status.AVAILABLE,
            purchase_date=None,
            expiry_date=None,
            notes=None,
        )
        db.session.add_all([a1, a2])
        db.session.commit()

        csrf = EmptyForm()
        kwargs = admin_requests_module._admin_request_review_template_kwargs(
            req=req,
            available_assets=[a1, a2],
            csrf_form=csrf,
            selected_asset_id="5",
            selected_return_due="2026-12-01",
            selected_asset_notes="hello",
        )

        assert kwargs["csrf_form"] is csrf
        assert kwargs["selected_asset_id"] == "5"
        assert kwargs["selected_return_due"] == "2026-12-01"
        assert kwargs["selected_asset_notes"] == "hello"
        assert kwargs["req"] is req
        assert kwargs["assets_notes_by_id"] == {
            str(a1.id): "  trimmed  ",
            str(a2.id): "",
        }
