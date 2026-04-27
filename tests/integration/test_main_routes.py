"""Integration tests for main blueprint (core, admin_requests, user_portal)."""

from __future__ import annotations

from datetime import date, timedelta
from unittest import mock
from unittest.mock import MagicMock

from sqlalchemy import select

from app.enums import AssetType, AuditAction, RequestStatus, Status
from app.extensions import db
from app.models import Asset, AssetRequest, Assignment, AuditLog, User


def _login(client, *, username: str, password: str) -> None:
    client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_index_redirects_to_login(client):
    rv = client.get("/", follow_redirects=False)
    assert rv.status_code == 302
    assert "/auth/login" in rv.headers["Location"]


def test_health_returns_json(client):
    rv = client.get("/health", follow_redirects=False)
    assert rv.status_code == 200
    assert rv.get_json() == {"healthy": True}


def test_dashboard_admin_ok(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.get("/dashboard", follow_redirects=False)
    assert rv.status_code == 200


def test_dashboard_standard_user_redirects_to_my_assets(client, credentials_user):
    _login(
        client,
        username=credentials_user["username"],
        password=credentials_user["password"],
    )
    rv = client.get("/dashboard", follow_redirects=False)
    assert rv.status_code == 302
    assert "/my-assets" in rv.headers["Location"]


def test_admin_requests_requires_login(client):
    rv = client.get("/admin/requests", follow_redirects=False)
    assert rv.status_code == 302


def test_admin_requests_denies_standard_user(client, credentials_user):
    _login(
        client,
        username=credentials_user["username"],
        password=credentials_user["password"],
    )
    rv = client.get("/admin/requests", follow_redirects=False)
    assert rv.status_code == 302
    assert "/my-assets" in rv.headers["Location"]


def test_admin_requests_list_filters(client, app, credentials_admin, credentials_user):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        alice = db.session.scalar(select(User).where(User.username == "alice"))
        assert alice is not None
        db.session.add(
            AssetRequest(
                user_id=alice.id,
                asset_type=AssetType.MONITOR,
                status=RequestStatus.PENDING,
                note="need monitor",
            ),
        )
        db.session.commit()

    rv = client.get(
        "/admin/requests?asset_type=MONITOR&request_status=PENDING",
        follow_redirects=False,
    )
    assert rv.status_code == 200


def test_admin_review_missing_redirects(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.get("/admin/requests/999999", follow_redirects=False)
    assert rv.status_code == 302
    assert "/admin/requests" in rv.headers["Location"]


def _seed_laptop_request_and_asset(app):
    with app.app_context():
        alice = db.session.scalar(select(User).where(User.username == "alice"))
        assert alice is not None
        asset = Asset(
            name="Pool Laptop",
            serial_number="MAIN-POOL-LP-1",
            asset_type=AssetType.LAPTOP,
            status=Status.AVAILABLE,
            purchase_date=date(2024, 1, 1),
            expiry_date=None,
            notes=None,
        )
        db.session.add(asset)
        db.session.flush()
        ar = AssetRequest(
            user_id=alice.id,
            asset_type=AssetType.LAPTOP,
            status=RequestStatus.PENDING,
            note="Need laptop",
        )
        db.session.add(ar)
        db.session.commit()
        return ar.id, asset.id


def test_admin_review_approve_assigns_and_audits(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rid, aid = _seed_laptop_request_and_asset(app)

    rv = client.post(
        f"/admin/requests/{rid}",
        data={
            "decision_action": "approve",
            "asset_id": str(aid),
            "return_due_date": (date.today() + timedelta(days=7)).isoformat(),
            "asset_notes": "  issued from pool  ",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert "/admin/requests" in rv.headers["Location"]

    with app.app_context():
        req = db.session.get(AssetRequest, rid)
        asset = db.session.get(Asset, aid)
        assert req is not None and req.status == RequestStatus.APPROVED
        assert asset is not None and asset.status == Status.ASSIGNED
        audit = db.session.scalar(
            select(AuditLog)
            .where(AuditLog.action == AuditAction.ASSET_ASSIGNED)
            .order_by(AuditLog.id.desc())
            .limit(1),
        )
        assert audit is not None
        assert "via request" in (audit.details or "").lower()


def test_admin_review_reject(app, client, credentials_admin, credentials_user):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rid, _ = _seed_laptop_request_and_asset(app)

    rv = client.post(
        f"/admin/requests/{rid}",
        data={"decision_action": "reject"},
        follow_redirects=False,
    )
    assert rv.status_code == 302

    with app.app_context():
        req = db.session.get(AssetRequest, rid)
        assert req is not None and req.status == RequestStatus.REJECTED


def test_admin_review_non_pending_redirects(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        alice = db.session.scalar(select(User).where(User.username == "alice"))
        assert alice is not None
        ar = AssetRequest(
            user_id=alice.id,
            asset_type=AssetType.LICENSE,
            status=RequestStatus.APPROVED,
            note="done",
        )
        db.session.add(ar)
        db.session.commit()
        rid = ar.id

    rv = client.post(
        f"/admin/requests/{rid}",
        data={"decision_action": "approve", "asset_id": "1"},
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert f"/admin/requests/{rid}" in rv.headers["Location"]


def test_admin_review_approve_notes_too_long(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rid, aid = _seed_laptop_request_and_asset(app)

    rv = client.post(
        f"/admin/requests/{rid}",
        data={
            "decision_action": "approve",
            "asset_id": str(aid),
            "asset_notes": "x" * 4001,
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200


def test_admin_review_approve_invalid_return_due(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rid, aid = _seed_laptop_request_and_asset(app)

    rv = client.post(
        f"/admin/requests/{rid}",
        data={
            "decision_action": "approve",
            "asset_id": str(aid),
            "return_due_date": "not-a-date",
            "asset_notes": "",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200


def test_admin_review_approve_return_due_before_today(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rid, aid = _seed_laptop_request_and_asset(app)
    past = date.today() - timedelta(days=3)

    rv = client.post(
        f"/admin/requests/{rid}",
        data={
            "decision_action": "approve",
            "asset_id": str(aid),
            "return_due_date": past.isoformat(),
            "asset_notes": "",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200


def test_admin_review_approve_no_asset_selected(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rid, _ = _seed_laptop_request_and_asset(app)

    rv = client.post(
        f"/admin/requests/{rid}",
        data={
            "decision_action": "approve",
            "asset_id": "",
            "asset_notes": "",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200


def test_admin_review_approve_wrong_asset_type_redirects(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rid, _ = _seed_laptop_request_and_asset(app)
    with app.app_context():
        other = Asset(
            name="Monitor pool",
            serial_number="MAIN-WT-1",
            asset_type=AssetType.MONITOR,
            status=Status.AVAILABLE,
            purchase_date=date(2024, 1, 1),
            expiry_date=None,
            notes=None,
        )
        db.session.add(other)
        db.session.commit()
        wrong_aid = other.id

    rv = client.post(
        f"/admin/requests/{rid}",
        data={
            "decision_action": "approve",
            "asset_id": str(wrong_aid),
            "asset_notes": "",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert f"/admin/requests/{rid}" in rv.headers["Location"]
    with app.app_context():
        req = db.session.get(AssetRequest, rid)
        assert req is not None and req.status == RequestStatus.PENDING


def test_admin_review_invalid_action_redirects(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rid, aid = _seed_laptop_request_and_asset(app)

    rv = client.post(
        f"/admin/requests/{rid}",
        data={
            "decision_action": "maybe",
            "asset_id": str(aid),
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302


def test_my_assets_requires_login(client):
    rv = client.get("/my-assets", follow_redirects=False)
    assert rv.status_code == 302


def test_my_assets_admin_redirected(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.get("/my-assets", follow_redirects=False)
    assert rv.status_code == 302
    assert "/dashboard" in rv.headers["Location"]


def test_request_asset_and_list(app, client, credentials_user):
    _login(
        client,
        username=credentials_user["username"],
        password=credentials_user["password"],
    )
    rv = client.post(
        "/my-assets/request",
        data={
            "asset_type": "MOUSE",
            "note": "Need a mouse for testing.",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert "/my-assets/requests" in rv.headers["Location"]

    rv2 = client.get("/my-assets/requests", follow_redirects=False)
    assert rv2.status_code == 200
    assert "MOUSE".lower() in rv2.get_data(as_text=True).lower()


def test_my_assets_history_ok(client, credentials_user):
    _login(
        client,
        username=credentials_user["username"],
        password=credentials_user["password"],
    )
    rv = client.get("/my-assets/history", follow_redirects=False)
    assert rv.status_code == 200


def test_edit_my_request_updates_note(app, client, credentials_user):
    _login(
        client,
        username=credentials_user["username"],
        password=credentials_user["password"],
    )
    with app.app_context():
        uid = db.session.scalar(select(User.id).where(User.username == "alice"))
        ar = AssetRequest(
            user_id=uid,
            asset_type=AssetType.KEYBOARD,
            status=RequestStatus.PENDING,
            note="old",
        )
        db.session.add(ar)
        db.session.commit()
        rid = ar.id

    rv = client.post(
        f"/my-assets/requests/{rid}/edit",
        data={"note": "new note text"},
        follow_redirects=False,
    )
    assert rv.status_code == 302

    with app.app_context():
        row = db.session.get(AssetRequest, rid)
        assert row is not None
        assert row.note == "new note text"


def test_delete_my_request_success(app, client, credentials_user):
    _login(
        client,
        username=credentials_user["username"],
        password=credentials_user["password"],
    )
    with app.app_context():
        uid = db.session.scalar(select(User.id).where(User.username == "alice"))
        ar = AssetRequest(
            user_id=uid,
            asset_type=AssetType.WEBCAM,
            status=RequestStatus.PENDING,
            note="cancel me",
        )
        db.session.add(ar)
        db.session.commit()
        rid = ar.id

    rv = client.post(
        f"/my-assets/requests/{rid}/delete",
        data={},
        follow_redirects=False,
    )
    assert rv.status_code == 302
    with app.app_context():
        assert db.session.get(AssetRequest, rid) is None


def test_delete_my_request_invalid_csrf(client, credentials_user):
    _login(
        client,
        username=credentials_user["username"],
        password=credentials_user["password"],
    )
    fake_form = MagicMock()
    fake_form.validate_on_submit.return_value = False
    with mock.patch("app.routes.main.user_portal.EmptyForm", return_value=fake_form):
        rv = client.post(
            "/my-assets/requests/1/delete", data={}, follow_redirects=False
        )
    assert rv.status_code == 302


def test_return_my_asset_success(app, client, credentials_user):
    _login(
        client,
        username=credentials_user["username"],
        password=credentials_user["password"],
    )
    with app.app_context():
        uid = db.session.scalar(select(User.id).where(User.username == "alice"))
        asset = Asset(
            name="Loaner",
            serial_number="RET-MAIN-1",
            asset_type=AssetType.LAPTOP,
            status=Status.ASSIGNED,
            purchase_date=date(2024, 1, 1),
            expiry_date=None,
            notes=None,
        )
        db.session.add(asset)
        db.session.flush()
        asn = Assignment(
            asset_id=asset.id,
            user_id=uid,
            assigned_date=date.today(),
            return_due_date=None,
            returned_date=None,
        )
        db.session.add(asn)
        db.session.commit()
        aid = asset.id

    rv = client.post(f"/my-assets/{aid}/return", data={}, follow_redirects=False)
    assert rv.status_code == 302

    with app.app_context():
        a = db.session.get(Asset, aid)
        assert a is not None and a.status == Status.RETURNED


def test_return_my_asset_no_assignment_flash(client, credentials_user):
    _login(
        client,
        username=credentials_user["username"],
        password=credentials_user["password"],
    )
    rv = client.post("/my-assets/999999/return", data={}, follow_redirects=False)
    assert rv.status_code == 302
