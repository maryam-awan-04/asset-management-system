from __future__ import annotations

from datetime import date
from enum import Enum
from typing import TypeVar

from flask import (
    Blueprint,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.access import admin_required
from app.enums import AssetType, AuditAction, Status
from app.extensions import db
from app.forms.asset import AssetCreateForm, AssetEditForm
from app.forms.empty import EmptyForm
from app.models import Asset, Assignment, AuditLog, User

bp = Blueprint("assets", __name__, url_prefix="/assets")

E = TypeVar("E", bound=Enum)


def _enum_by_name(enum_cls: type[E], raw: str) -> E | None:
    key = raw.strip()
    if not key:
        return None
    try:
        return enum_cls[key.upper()]
    except KeyError:
        return None


def _audit(user_id: int | None, action: AuditAction, details: str | None) -> None:
    db.session.add(AuditLog(user_id=user_id, action=action, details=details))


def _active_open_assignment(asset: Asset) -> Assignment | None:
    return db.session.scalar(
        select(Assignment)
        .where(
            Assignment.asset_id == asset.id,
            Assignment.returned_date.is_(None),
        )
        .order_by(Assignment.assigned_date.desc())
        .limit(1),
    )


def _active_assignment_user_id(asset: Asset) -> int | None:
    row = _active_open_assignment(asset)
    return row.user_id if row else None


def _close_open_assignments(asset: Asset, as_of: date) -> None:
    for row in db.session.scalars(
        select(Assignment).where(
            Assignment.asset_id == asset.id,
            Assignment.returned_date.is_(None),
        ),
    ):
        row.returned_date = as_of


def _assign_user_label(user_id: int | None) -> str:
    if user_id is None:
        return ""
    user = db.session.get(User, user_id)
    if user is None:
        return ""
    return f"{user.username} — {user.email} ({user.department.value})"


def _snapshot_asset(asset: Asset) -> dict:
    return {
        "name": asset.name,
        "serial_number": asset.serial_number,
        "asset_type": asset.asset_type,
        "status": asset.status,
        "purchase_date": asset.purchase_date,
        "expiry_date": asset.expiry_date,
        "notes": asset.notes,
    }


def _norm_notes(val: str | None) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def _display_audit_value(val: object, max_len: int = 72) -> str:
    if val is None:
        return "—"
    if isinstance(val, Enum):
        return str(val.value)
    if isinstance(val, date):
        return val.isoformat()
    s = str(val).replace("\n", " ").strip()
    if not s:
        return "—"
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def _build_asset_update_audit_details(before: dict, asset: Asset) -> str:
    sn = asset.serial_number
    nm = asset.name
    pairs: list[tuple[str, object, object]] = [
        ("name", before["name"], asset.name),
        ("serial", before["serial_number"], asset.serial_number),
        ("type", before["asset_type"], asset.asset_type),
        ("status", before["status"], asset.status),
        ("purchase", before["purchase_date"], asset.purchase_date),
        ("expiry", before["expiry_date"], asset.expiry_date),
        ("notes", _norm_notes(before["notes"]), _norm_notes(asset.notes)),
    ]
    changes: list[str] = []
    for label, old, new in pairs:
        if old != new:
            changes.append(
                f"{label}: {_display_audit_value(old)}→{_display_audit_value(new)}",
            )
    inner = "; ".join(changes) if changes else "fields unchanged"
    return f"{sn}: {nm} | {inner}"


@bp.get("/assignable-users")
@admin_required
def search_assignable_users():
    q = (request.args.get("q") or "").strip()
    if len(q) < 1:
        return jsonify([])
    q = q[:80].replace("%", "").replace("_", "")
    if not q:
        return jsonify([])
    pattern = f"%{q}%"
    users = db.session.scalars(
        select(User)
        .where(
            or_(
                User.username.ilike(pattern),
                User.email.ilike(pattern),
            ),
        )
        .order_by(User.username.asc())
        .limit(25),
    ).all()
    return jsonify(
        [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "department": u.department.value,
            }
            for u in users
        ],
    )


@bp.get("/")
@admin_required
def list_assets():
    stmt = select(Asset).order_by(Asset.name.asc())

    raw_type = request.args.get("asset_type", "")
    raw_status = request.args.get("status", "")

    type_member = _enum_by_name(AssetType, raw_type)
    status_member = _enum_by_name(Status, raw_status)

    type_key = type_member.name if type_member is not None else ""
    status_key = status_member.name if status_member is not None else ""

    if type_member is not None:
        stmt = stmt.where(Asset.asset_type == type_member)
    if status_member is not None:
        stmt = stmt.where(Asset.status == status_member)

    assets = db.session.scalars(stmt).all()
    html = render_template(
        "assets/list.html",
        assets=assets,
        filter_asset_type=type_key,
        filter_status=status_key,
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@bp.get("/<int:asset_id>/view")
@admin_required
def view_asset(asset_id: int):
    asset = db.session.get(Asset, asset_id)
    if asset is None:
        flash("That asset could not be found.", "warning")
        return redirect(url_for("assets.list_assets"))

    assignments = db.session.scalars(
        select(Assignment)
        .where(Assignment.asset_id == asset.id)
        .options(joinedload(Assignment.user))
        .order_by(Assignment.assigned_date.desc(), Assignment.id.desc()),
    ).all()

    serial = asset.serial_number
    audit_stmt = (
        select(AuditLog)
        .where(
            AuditLog.details.isnot(None),
            AuditLog.details.contains(serial),
        )
        .options(joinedload(AuditLog.user))
        .order_by(AuditLog.timestamp.desc())
        .limit(50)
    )
    audit_logs = db.session.scalars(audit_stmt).unique().all()

    html = render_template(
        "assets/detail.html",
        asset=asset,
        assignments=assignments,
        audit_logs=audit_logs,
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def new_asset():
    form = AssetCreateForm()
    if form.validate_on_submit():
        asset = Asset(
            name=form.name.data.strip(),
            serial_number=form.serial_number.data.strip(),
            asset_type=form.asset_type.data,
            status=form.status.data,
            purchase_date=form.purchase_date.data,
            expiry_date=form.expiry_date.data,
            notes=(form.notes.data or "").strip() or None,
        )
        db.session.add(asset)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            flash(
                "Could not create this asset. Serial number already exists.",
                "danger",
            )
            return render_template("assets/new.html", form=form)
        _audit(
            current_user.id,
            AuditAction.ASSET_CREATED,
            f"{asset.serial_number}: {asset.name} | created as "
            f"{asset.asset_type.value}; status {asset.status.value}",
        )
        db.session.commit()
        flash("Asset created.", "success")
        return redirect(url_for("assets.list_assets"))

    return render_template("assets/new.html", form=form)


@bp.route("/<int:asset_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_asset(asset_id: int):
    asset = db.session.get(Asset, asset_id)
    if asset is None:
        flash("That asset could not be found.", "warning")
        return redirect(url_for("assets.list_assets"))

    today = date.today()
    active_uid = _active_assignment_user_id(asset)

    if request.method == "GET":
        data: dict = {
            "name": asset.name,
            "serial_number": asset.serial_number,
            "asset_type": asset.asset_type.name,
            "status": asset.status.name,
            "purchase_date": asset.purchase_date,
            "expiry_date": asset.expiry_date,
            "notes": asset.notes or "",
        }
        if active_uid is not None:
            data["assign_user_id"] = str(active_uid)
        open_row = _active_open_assignment(asset)
        if open_row is not None and open_row.return_due_date is not None:
            data["assignment_return_due"] = open_row.return_due_date
        form = AssetEditForm(asset_id=asset.id, data=data)
    else:
        form = AssetEditForm(asset_id=asset.id, formdata=request.form)

    if form.validate_on_submit():
        active_before = _active_assignment_user_id(asset)
        assign_raw = (form.assign_user_id.data or "").strip()
        assign_uid = int(assign_raw) if assign_raw.isdigit() else None

        if form.status.data != Status.ASSIGNED and active_before is not None:
            flash(
                "This asset is assigned to a user. They must return it before the status can be changed.",
                "danger",
            )
            return render_template(
                "assets/edit.html",
                form=form,
                asset=asset,
                assign_user_display=_assign_user_label(
                    assign_uid if assign_raw.isdigit() else active_before,
                ),
                search_users_url=url_for("assets.search_assignable_users"),
            )

        due_back = form.assignment_return_due.data

        before = _snapshot_asset(asset)
        asset.name = form.name.data.strip()
        asset.serial_number = form.serial_number.data.strip()
        asset.asset_type = form.asset_type.data
        asset.status = form.status.data
        asset.purchase_date = form.purchase_date.data
        asset.expiry_date = form.expiry_date.data
        asset.notes = (form.notes.data or "").strip() or None
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            flash(
                "Could not save changes. Serial number already exists.",
                "danger",
            )
            return render_template(
                "assets/edit.html",
                form=form,
                asset=asset,
                assign_user_display=_assign_user_label(
                    (
                        int(form.assign_user_id.data)
                        if (form.assign_user_id.data or "").strip().isdigit()
                        else None
                    ),
                ),
                search_users_url=url_for("assets.search_assignable_users"),
            )

        if form.status.data == Status.ASSIGNED and assign_uid is not None:
            if assign_uid != active_before:
                _close_open_assignments(asset, today)
                db.session.add(
                    Assignment(
                        asset_id=asset.id,
                        user_id=assign_uid,
                        assigned_date=today,
                        return_due_date=due_back,
                        returned_date=None,
                    ),
                )
                assignee = db.session.get(User, assign_uid)
                assignee_name = assignee.username if assignee else "unknown user"
                due_note = f"; return due {due_back.isoformat()}" if due_back else ""
                _audit(
                    current_user.id,
                    AuditAction.ASSET_ASSIGNED,
                    f"{asset.serial_number}: {asset.name} | assigned to "
                    f"{assignee_name} (user id {assign_uid}){due_note}",
                )
            else:
                open_row = _active_open_assignment(asset)
                if open_row is not None and open_row.user_id == assign_uid:
                    open_row.return_due_date = due_back

        _audit(
            current_user.id,
            AuditAction.ASSET_UPDATED,
            _build_asset_update_audit_details(before, asset),
        )
        db.session.commit()
        flash("Asset updated.", "success")
        return redirect(url_for("assets.list_assets"))

    raw_uid = (form.assign_user_id.data or "").strip()
    assign_uid = int(raw_uid) if raw_uid.isdigit() else None
    return render_template(
        "assets/edit.html",
        form=form,
        asset=asset,
        assign_user_display=_assign_user_label(assign_uid),
        search_users_url=url_for("assets.search_assignable_users"),
    )


@bp.post("/<int:asset_id>/delete")
@admin_required
def delete_asset(asset_id: int):
    form = EmptyForm()
    if not form.validate_on_submit():
        flash("Could not delete the asset. Please try again.", "danger")
        return redirect(url_for("assets.list_assets"))

    asset = db.session.get(Asset, asset_id)
    if asset is None:
        flash("That asset no longer exists.", "warning")
        return redirect(url_for("assets.list_assets"))

    if asset.status == Status.ASSIGNED:
        flash(
            "Cannot delete an asset while its status is Assigned. "
            "Have the assignee return it from My assigned assets (or change status) first.",
            "danger",
        )
        return redirect(url_for("assets.list_assets"))

    label = f"{asset.name} ({asset.serial_number})"
    db.session.delete(asset)
    _audit(current_user.id, AuditAction.ASSET_DELETED, label)
    db.session.commit()
    flash(f"Deleted asset {label}.", "info")
    return redirect(url_for("assets.list_assets"))
