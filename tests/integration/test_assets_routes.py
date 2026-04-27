"""Integration tests for assets blueprint."""

from __future__ import annotations

from datetime import date, timedelta
from unittest import mock
from unittest.mock import MagicMock

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.enums import AssetType, AuditAction, Status
from app.extensions import db
from app.models import Asset, Assignment, AuditLog, User


def _login(client, *, username: str, password: str) -> None:
    client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def _create_asset(
    *,
    name: str = "Test Asset",
    serial: str = "ASSET-SN-001",
    asset_type: AssetType = AssetType.LAPTOP,
    status: Status = Status.AVAILABLE,
) -> Asset:
    row = Asset(
        name=name,
        serial_number=serial,
        asset_type=asset_type,
        status=status,
        purchase_date=date(2024, 1, 1),
        expiry_date=None,
        notes=None,
    )
    db.session.add(row)
    db.session.commit()
    return row


def test_assets_list_requires_login(client):
    rv = client.get("/assets/", follow_redirects=False)
    assert rv.status_code == 302
    assert "/auth/login" in rv.headers["Location"]


def test_assets_list_denies_standard_user(client, credentials_user):
    _login(
        client,
        username=credentials_user["username"],
        password=credentials_user["password"],
    )
    rv = client.get("/assets/", follow_redirects=False)
    assert rv.status_code == 302
    assert "/my-assets" in rv.headers["Location"]


def test_assets_list_admin_ok_cache_header(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.get("/assets/", follow_redirects=False)
    assert rv.status_code == 200
    assert "private, no-store" in rv.headers["Cache-Control"]


def test_list_assets_query_filters_and_overdue(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "alice"))
        assert user is not None
        _create_asset(
            name="Alpha Laptop",
            serial="LIST-LAP-1",
            asset_type=AssetType.LAPTOP,
            status=Status.AVAILABLE,
        )
        mon = _create_asset(
            name="Zeta Monitor",
            serial="LIST-MON-1",
            asset_type=AssetType.MONITOR,
            status=Status.ASSIGNED,
        )
        db.session.add(
            Assignment(
                asset_id=mon.id,
                user_id=user.id,
                assigned_date=date.today() - timedelta(days=3),
                return_due_date=date.today() - timedelta(days=1),
                returned_date=None,
            ),
        )
        nodue = _create_asset(
            name="No Due Asset",
            serial="LIST-NODUE-1",
            asset_type=AssetType.KEYBOARD,
            status=Status.ASSIGNED,
        )
        db.session.add(
            Assignment(
                asset_id=nodue.id,
                user_id=user.id,
                assigned_date=date.today(),
                return_due_date=None,
                returned_date=None,
            ),
        )
        db.session.commit()

    rv_type = client.get("/assets/?asset_type=LAPTOP", follow_redirects=False)
    assert rv_type.status_code == 200
    body_t = rv_type.get_data(as_text=True)
    assert "Alpha Laptop" in body_t
    assert "Zeta Monitor" not in body_t

    rv_status = client.get("/assets/?status=AVAILABLE", follow_redirects=False)
    assert rv_status.status_code == 200

    rv_over = client.get("/assets/?overdue=1", follow_redirects=False)
    assert rv_over.status_code == 200
    body_o = rv_over.get_data(as_text=True)
    assert "Zeta Monitor" in body_o
    assert "No Due Asset" not in body_o

    rv_all = client.get("/assets/", follow_redirects=False)
    assert rv_all.status_code == 200


def test_assignable_users_empty_when_query_missing(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.get("/assets/assignable-users", follow_redirects=False)
    assert rv.status_code == 200
    assert rv.get_json() == []


def test_assignable_users_returns_matching_user(
    client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.get("/assets/assignable-users?q=ali", follow_redirects=False)
    assert rv.status_code == 200
    rows = rv.get_json()
    assert isinstance(rows, list)
    assert any(row["username"] == credentials_user["username"] for row in rows)


def test_new_asset_post_creates_row_and_audit(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        before = db.session.scalar(select(func.count(Asset.id))) or 0

    rv = client.post(
        "/assets/new",
        data={
            "name": "Dell Workstation",
            "serial_number": "DL-NEW-1001",
            "asset_type": "LAPTOP",
            "status": "AVAILABLE",
            "purchase_date": "2024-02-01",
            "expiry_date": "",
            "notes": "Primary engineering workstation",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert "/assets/" in rv.headers["Location"]

    with app.app_context():
        after = db.session.scalar(select(func.count(Asset.id))) or 0
        created = db.session.scalar(
            select(Asset).where(Asset.serial_number == "DL-NEW-1001")
        )
        last_audit = db.session.scalar(
            select(AuditLog).order_by(AuditLog.id.desc()).limit(1),
        )
        assert after == before + 1
        assert created is not None
        assert last_audit is not None
        assert last_audit.action == AuditAction.ASSET_CREATED


def test_new_asset_duplicate_serial_rejected(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        _create_asset(serial="DUP-SN-1")
        before = db.session.scalar(select(func.count(Asset.id))) or 0

    rv = client.post(
        "/assets/new",
        data={
            "name": "Duplicate Serial Asset",
            "serial_number": "DUP-SN-1",
            "asset_type": "MONITOR",
            "status": "AVAILABLE",
            "purchase_date": "2024-02-01",
            "expiry_date": "",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200

    with app.app_context():
        after = db.session.scalar(select(func.count(Asset.id))) or 0
        assert after == before


def test_edit_asset_updates_fields(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        asset = _create_asset(name="Old Name", serial="EDIT-SN-1")
        asset_id = asset.id

    rv = client.post(
        f"/assets/{asset_id}/edit",
        data={
            "name": "Updated Name",
            "serial_number": "EDIT-SN-1",
            "asset_type": "LAPTOP",
            "status": "AVAILABLE",
            "purchase_date": "2024-01-01",
            "expiry_date": "",
            "notes": "Updated notes",
            "assign_user_id": "",
            "assignment_return_due": "",
            "returned_on": "",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert "/assets/" in rv.headers["Location"]

    with app.app_context():
        row = db.session.get(Asset, asset_id)
        assert row is not None
        assert row.name == "Updated Name"
        assert row.notes == "Updated notes"


def test_delete_asset_removes_available_asset(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        asset = _create_asset(serial="DEL-SN-1", status=Status.AVAILABLE)
        aid = asset.id

    rv = client.post(f"/assets/{aid}/delete", data={}, follow_redirects=False)
    assert rv.status_code == 302
    assert "/assets/" in rv.headers["Location"]

    with app.app_context():
        gone = db.session.get(Asset, aid)
        assert gone is None


def test_delete_asset_blocked_when_assigned(
    app,
    client,
    credentials_admin,
    credentials_user,
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "alice"))
        assert user is not None
        asset = _create_asset(serial="DEL-BLOCK-1", status=Status.ASSIGNED)
        db.session.add(
            Assignment(
                asset_id=asset.id,
                user_id=user.id,
                assigned_date=date.today(),
                return_due_date=None,
                returned_date=None,
            ),
        )
        db.session.commit()
        aid = asset.id

    rv = client.post(f"/assets/{aid}/delete", data={}, follow_redirects=False)
    assert rv.status_code == 302
    assert "/assets/" in rv.headers["Location"]

    with app.app_context():
        still_there = db.session.get(Asset, aid)
        assert still_there is not None


def test_view_asset_renders_and_cache_header(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        admin = db.session.scalar(
            select(User).where(User.username == credentials_admin["username"]),
        )
        assert admin is not None
        asset = _create_asset(name="View Me", serial="VIEW-SN-990")
        db.session.add(
            AuditLog(
                user_id=admin.id,
                action=AuditAction.ASSET_CREATED,
                details=f"{asset.serial_number}: created for view test",
            ),
        )
        db.session.commit()
        aid = asset.id

    rv = client.get(f"/assets/{aid}/view", follow_redirects=False)
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    assert "VIEW-SN-990" in html
    assert "private, no-store" in rv.headers["Cache-Control"]


def test_view_asset_missing_redirects(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.get("/assets/999999/view", follow_redirects=False)
    assert rv.status_code == 302
    assert "/assets/" in rv.headers["Location"]


def test_new_asset_flush_integrity_error_renders_form(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with mock.patch(
        "app.routes.assets.db.session.flush",
        side_effect=IntegrityError("stmt", {}, None),
    ):
        rv = client.post(
            "/assets/new",
            data={
                "name": "Integrity Asset",
                "serial_number": "INTEG-SN-1",
                "asset_type": "LAPTOP",
                "status": "AVAILABLE",
                "purchase_date": "2024-02-01",
                "expiry_date": "",
                "notes": "",
            },
            follow_redirects=False,
        )
    assert rv.status_code == 200


def test_edit_asset_missing_redirects(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.get("/assets/888888/edit", follow_redirects=False)
    assert rv.status_code == 302
    assert "/assets/" in rv.headers["Location"]


def test_edit_asset_get_prefills_assignment_fields(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "alice"))
        assert user is not None
        alice_id = user.id
        asset = _create_asset(serial="GET-EDIT-1", status=Status.ASSIGNED)
        due = date.today() + timedelta(days=7)
        db.session.add(
            Assignment(
                asset_id=asset.id,
                user_id=alice_id,
                assigned_date=date.today(),
                return_due_date=due,
                returned_date=None,
            ),
        )
        db.session.commit()
        aid = asset.id

    rv = client.get(f"/assets/{aid}/edit", follow_redirects=False)
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    assert str(alice_id) in html
    assert due.isoformat() in html


def test_edit_asset_flash_when_changing_non_return_status_while_assigned(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "alice"))
        assert user is not None
        asset = _create_asset(serial="BLOCK-ST-1", status=Status.ASSIGNED)
        db.session.add(
            Assignment(
                asset_id=asset.id,
                user_id=user.id,
                assigned_date=date.today(),
                return_due_date=None,
                returned_date=None,
            ),
        )
        db.session.commit()
        aid = asset.id

    rv = client.post(
        f"/assets/{aid}/edit",
        data={
            "name": "Blocked Status Change",
            "serial_number": "BLOCK-ST-1",
            "asset_type": "LAPTOP",
            "status": "AVAILABLE",
            "purchase_date": "2024-01-01",
            "expiry_date": "",
            "notes": "",
            "assign_user_id": "",
            "assignment_return_due": "",
            "returned_on": "",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200
    assert b"assigned to a user" in rv.data


def test_edit_asset_duplicate_serial_integrity_flash(app, client, credentials_admin):
    """DB-level duplicate serial on flush (validators do not catch every race)."""
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        asset = _create_asset(name="Rename Me", serial="RENAME-SN")
        aid = asset.id

    with mock.patch(
        "app.routes.assets.db.session.flush",
        side_effect=IntegrityError("stmt", {}, None),
    ):
        rv = client.post(
            f"/assets/{aid}/edit",
            data={
                "name": "Rename Me",
                "serial_number": "RENAME-SN",
                "asset_type": "LAPTOP",
                "status": "AVAILABLE",
                "purchase_date": "2024-01-01",
                "expiry_date": "",
                "notes": "",
                "assign_user_id": "",
                "assignment_return_due": "",
                "returned_on": "",
            },
            follow_redirects=False,
        )
    assert rv.status_code == 200
    assert b"Serial number already exists" in rv.data


def test_edit_asset_returned_closes_open_assignment(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "alice"))
        assert user is not None
        alice_id = user.id
        asset = _create_asset(serial="RET-ASN-1", status=Status.ASSIGNED)
        asn = Assignment(
            asset_id=asset.id,
            user_id=alice_id,
            assigned_date=date.today(),
            return_due_date=None,
            returned_date=None,
        )
        db.session.add(asn)
        db.session.commit()
        aid = asset.id
        asn_id = asn.id

    ret_on = date.today() - timedelta(days=1)
    rv = client.post(
        f"/assets/{aid}/edit",
        data={
            "name": "Returned Asset",
            "serial_number": "RET-ASN-1",
            "asset_type": "LAPTOP",
            "status": "RETURNED",
            "purchase_date": "2024-01-01",
            "expiry_date": "",
            "notes": "",
            "assign_user_id": str(alice_id),
            "assignment_return_due": "",
            "returned_on": ret_on.isoformat(),
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302

    with app.app_context():
        row = db.session.get(Assignment, asn_id)
        assert row is not None
        assert row.returned_date == ret_on


def test_edit_asset_assign_to_user_creates_assignment_and_audit(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "alice"))
        assert user is not None
        alice_id = user.id
        asset = _create_asset(serial="NEW-ASN-1", status=Status.AVAILABLE)
        db.session.commit()
        aid = asset.id

    due = date.today() + timedelta(days=14)
    rv = client.post(
        f"/assets/{aid}/edit",
        data={
            "name": "Now Assigned",
            "serial_number": "NEW-ASN-1",
            "asset_type": "LAPTOP",
            "status": "ASSIGNED",
            "purchase_date": "2024-01-01",
            "expiry_date": "",
            "notes": "",
            "assign_user_id": str(alice_id),
            "assignment_return_due": due.isoformat(),
            "returned_on": "",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302

    with app.app_context():
        asset = db.session.get(Asset, aid)
        assert asset is not None
        assert asset.status == Status.ASSIGNED
        assign_audit = db.session.scalar(
            select(AuditLog)
            .where(AuditLog.action == AuditAction.ASSET_ASSIGNED)
            .order_by(AuditLog.id.desc())
            .limit(1),
        )
        assert assign_audit is not None
        assert "alice" in (assign_audit.details or "").lower()


def test_edit_asset_validation_error_renders_edit_template(
    app, client, credentials_admin
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        asset = _create_asset(serial="BAD-FORM-1")
        aid = asset.id

    rv = client.post(
        f"/assets/{aid}/edit",
        data={
            "name": "",
            "serial_number": "BAD-FORM-1",
            "asset_type": "LAPTOP",
            "status": "AVAILABLE",
            "purchase_date": "2024-01-01",
            "expiry_date": "",
            "notes": "",
            "assign_user_id": "",
            "assignment_return_due": "",
            "returned_on": "",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200


def test_delete_asset_not_found_redirects(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.post("/assets/999999/delete", data={}, follow_redirects=False)
    assert rv.status_code == 302
    assert "/assets/" in rv.headers["Location"]


def test_delete_asset_invalid_csrf_form_rejected(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    fake_form = MagicMock()
    fake_form.validate_on_submit.return_value = False
    with mock.patch("app.routes.assets.EmptyForm", return_value=fake_form):
        rv = client.post("/assets/1/delete", data={}, follow_redirects=False)
    assert rv.status_code == 302
    assert "/assets/" in rv.headers["Location"]
