"""Unit tests for asset route helpers."""

from __future__ import annotations

from datetime import date

from app.enums import AssetType, Department, Role, Status
from app.extensions import db
from app.models import Asset, Assignment, User
from app.passwords import hash_password
from app.routes.assets import (
    _assign_user_label,
    _close_open_assignments,
    _display_audit_value,
)


def test_display_audit_value():
    assert _display_audit_value(AssetType.LAPTOP) == "Laptop"


def test_display_audit_value_date():
    assert _display_audit_value(date(2024, 6, 1)) == "2024-06-01"


def test_display_audit_value_empty_after_strip():
    assert _display_audit_value("   \n  ") == "—"


def test_display_audit_value_truncates_long_string():
    long_s = "x" * 100
    out = _display_audit_value(long_s, max_len=72)
    assert len(out) == 72
    assert out.endswith("…")


def test_assign_user_label_none_and_missing_user(app):
    with app.app_context():
        assert _assign_user_label(None) == ""
        assert _assign_user_label(999_999) == ""


def test_close_open_assignments_sets_returned_dates(app):
    with app.app_context():
        user = User(
            username="assignee_close",
            email="assignee_close@example.com",
            password_hash=hash_password("Pw1!aaaa"),
            role=Role.USER,
            department=Department.TECHNOLOGY,
        )
        db.session.add(user)
        db.session.flush()
        asset = Asset(
            name="Close Me",
            serial_number="CLOSE-SN-1",
            asset_type=AssetType.MONITOR,
            status=Status.ASSIGNED,
            purchase_date=None,
            expiry_date=None,
            notes=None,
        )
        db.session.add(asset)
        db.session.flush()
        row = Assignment(
            asset_id=asset.id,
            user_id=user.id,
            assigned_date=date.today(),
            return_due_date=None,
            returned_date=None,
        )
        db.session.add(row)
        db.session.commit()

        closed_on = date(2025, 3, 15)
        _close_open_assignments(asset, closed_on)
        db.session.commit()

        db.session.refresh(row)
        assert row.returned_date == closed_on
