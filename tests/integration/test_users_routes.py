"""Integration tests for users blueprint."""

from __future__ import annotations

from datetime import date
from unittest import mock
from unittest.mock import MagicMock

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.enums import AssetType, AuditAction, Department, Role, Status
from app.extensions import db
from app.models import Asset, Assignment, AuditLog, User
from app.passwords import hash_password


def _login(client, *, username: str, password: str) -> None:
    client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def _make_user_db(
    *,
    username: str,
    email: str,
    role: Role = Role.USER,
    department: Department = Department.TECHNOLOGY,
) -> int:
    u = User(
        username=username,
        email=email,
        password_hash=hash_password("Valid1!Password"),
        role=role,
        department=department,
    )
    db.session.add(u)
    db.session.commit()
    return u.id


def test_users_list_requires_login(client):
    rv = client.get("/users/", follow_redirects=False)
    assert rv.status_code == 302
    assert "/auth/login" in rv.headers["Location"]


def test_users_list_denies_non_admin(client, credentials_user):
    _login(
        client,
        username=credentials_user["username"],
        password=credentials_user["password"],
    )
    rv = client.get("/users/", follow_redirects=False)
    assert rv.status_code == 302
    assert "/my-assets" in rv.headers["Location"]


def test_users_list_admin_ok_cache(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.get("/users/", follow_redirects=False)
    assert rv.status_code == 200
    assert "private, no-store" in rv.headers["Cache-Control"]


def test_users_list_filters_and_list_results(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        _make_user_db(
            username="filter_fin",
            email="filter_fin@example.com",
            department=Department.FINANCE,
        )

    rv_dept = client.get("/users/?department=FINANCE", follow_redirects=False)
    assert rv_dept.status_code == 200
    assert "filter_fin" in rv_dept.get_data(as_text=True)

    rv_role = client.get("/users/?role=ADMIN", follow_redirects=False)
    assert rv_role.status_code == 200

    rv_q = client.get("/users/?q=bob", follow_redirects=False)
    assert rv_q.status_code == 200
    assert "adminbob" in rv_q.get_data(as_text=True)

    rv_part = client.get("/users/list-results?q=bob", follow_redirects=False)
    assert rv_part.status_code == 200
    assert "private, no-store" in rv_part.headers["Cache-Control"]


def test_view_user_assets_missing_redirects(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.get("/users/999999/assets", follow_redirects=False)
    assert rv.status_code == 302
    assert "/users/" in rv.headers["Location"]


def test_view_user_assets_splits_current_and_past(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        uid = db.session.scalar(select(User.id).where(User.username == "alice"))
        assert uid is not None
        asset_open = Asset(
            name="Open",
            serial_number="USR-OPEN-1",
            asset_type=AssetType.LAPTOP,
            status=Status.ASSIGNED,
            purchase_date=date(2024, 1, 1),
            expiry_date=None,
            notes=None,
        )
        asset_past = Asset(
            name="Past",
            serial_number="USR-PAST-1",
            asset_type=AssetType.MOUSE,
            status=Status.RETURNED,
            purchase_date=date(2024, 1, 1),
            expiry_date=None,
            notes=None,
        )
        db.session.add_all([asset_open, asset_past])
        db.session.flush()
        db.session.add(
            Assignment(
                asset_id=asset_open.id,
                user_id=uid,
                assigned_date=date.today(),
                return_due_date=None,
                returned_date=None,
            ),
        )
        db.session.add(
            Assignment(
                asset_id=asset_past.id,
                user_id=uid,
                assigned_date=date(2023, 1, 1),
                return_due_date=None,
                returned_date=date(2024, 1, 1),
            ),
        )
        db.session.commit()

    rv = client.get(f"/users/{uid}/assets", follow_redirects=False)
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    assert "Open" in html
    assert "Past" in html


def test_edit_user_missing_redirects(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.get("/users/888888/edit", follow_redirects=False)
    assert rv.status_code == 302
    assert "/users/" in rv.headers["Location"]


def test_edit_user_updates_and_writes_audit(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        uid = _make_user_db(
            username="editme",
            email="editme@example.com",
            department=Department.HR,
        )

    rv = client.post(
        f"/users/{uid}/edit",
        data={
            "username": "edited_name",
            "role": "USER",
            "department": "LEGAL",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert "/users/" in rv.headers["Location"]

    with app.app_context():
        row = db.session.get(User, uid)
        assert row is not None
        assert row.username == "edited_name"
        assert row.department == Department.LEGAL
        audit = db.session.scalar(
            select(AuditLog)
            .where(AuditLog.action == AuditAction.USER_UPDATED)
            .order_by(AuditLog.id.desc())
            .limit(1),
        )
        assert audit is not None
        assert "edited_name" in (audit.details or "")


def test_edit_user_sole_admin_cannot_demote_self(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        uid = db.session.scalar(
            select(User.id).where(User.username == "adminbob"),
        )
        assert uid is not None

    rv = client.post(
        f"/users/{uid}/edit",
        data={
            "username": "adminbob",
            "role": "USER",
            "department": "TECHNOLOGY",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200
    assert b"only admin" in rv.data.lower()


def test_edit_user_integrity_error_flash(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        uid = _make_user_db(username="flushme", email="flushme@example.com")

    with mock.patch(
        "app.routes.users.db.session.flush",
        side_effect=IntegrityError("stmt", {}, None),
    ):
        rv = client.post(
            f"/users/{uid}/edit",
            data={
                "username": "flushme",
                "role": "USER",
                "department": "TECHNOLOGY",
            },
            follow_redirects=False,
        )
    assert rv.status_code == 200
    assert b"username may already be in use" in rv.data.lower()


def test_edit_user_validation_error_renders_edit_template(
    app, client, credentials_admin
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        uid = _make_user_db(username="validlen", email="vl@example.com")

    rv = client.post(
        f"/users/{uid}/edit",
        data={
            "username": "ab",
            "role": "USER",
            "department": "TECHNOLOGY",
        },
        follow_redirects=False,
    )
    assert rv.status_code == 200


def test_delete_user_invalid_form_redirects(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    fake_form = MagicMock()
    fake_form.validate_on_submit.return_value = False
    with mock.patch("app.routes.users.EmptyForm", return_value=fake_form):
        rv = client.post("/users/1/delete", data={}, follow_redirects=False)
    assert rv.status_code == 302
    assert "/users/" in rv.headers["Location"]


def test_delete_user_missing_redirects(client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    rv = client.post("/users/999999/delete", data={}, follow_redirects=False)
    assert rv.status_code == 302
    assert "/users/" in rv.headers["Location"]


def test_delete_user_cannot_delete_self_blocks(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        uid = db.session.scalar(select(User.id).where(User.username == "adminbob"))

    rv = client.post(f"/users/{uid}/delete", data={}, follow_redirects=False)
    assert rv.status_code == 302
    assert "/users/" in rv.headers["Location"]
    with app.app_context():
        assert db.session.get(User, uid) is not None


def test_delete_user_blocked_with_open_assignment(
    app, client, credentials_admin, credentials_user
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        uid = db.session.scalar(select(User.id).where(User.username == "alice"))
        asset = Asset(
            name="Held",
            serial_number="DEL-BLOCK-U1",
            asset_type=AssetType.KEYBOARD,
            status=Status.ASSIGNED,
            purchase_date=date(2024, 1, 1),
            expiry_date=None,
            notes=None,
        )
        db.session.add(asset)
        db.session.flush()
        db.session.add(
            Assignment(
                asset_id=asset.id,
                user_id=uid,
                assigned_date=date.today(),
                return_due_date=None,
                returned_date=None,
            ),
        )
        db.session.commit()

    rv = client.post(f"/users/{uid}/delete", data={}, follow_redirects=False)
    assert rv.status_code == 302
    with app.app_context():
        assert db.session.get(User, uid) is not None


def test_delete_user_blocked_only_administrator(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        other_id = _make_user_db(
            username="otheradm",
            email="otheradm@example.com",
            role=Role.ADMIN,
            department=Department.STS,
        )

    call_n = {"n": 0}

    def _scalar(stmt):
        call_n["n"] += 1
        if call_n["n"] == 1:
            return 0
        return 1

    with mock.patch.object(db.session, "scalar", side_effect=_scalar):
        rv = client.post(f"/users/{other_id}/delete", data={}, follow_redirects=False)

    assert rv.status_code == 302
    with app.app_context():
        assert db.session.get(User, other_id) is not None


def test_delete_user_success_regular_user(app, client, credentials_admin):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        uid = _make_user_db(username="todelete", email="td@example.com")

    rv = client.post(f"/users/{uid}/delete", data={}, follow_redirects=False)
    assert rv.status_code == 302

    with app.app_context():
        assert db.session.get(User, uid) is None


def test_delete_second_admin_allowed_when_multiple_admins_exist(
    app, client, credentials_admin
):
    _login(
        client,
        username=credentials_admin["username"],
        password=credentials_admin["password"],
    )
    with app.app_context():
        extra_id = _make_user_db(
            username="extraadm",
            email="extraadm@example.com",
            role=Role.ADMIN,
            department=Department.CP,
        )

    rv = client.post(f"/users/{extra_id}/delete", data={}, follow_redirects=False)
    assert rv.status_code == 302

    with app.app_context():
        assert db.session.get(User, extra_id) is None
