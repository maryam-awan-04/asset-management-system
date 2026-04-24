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


def _active_assignment_user_id(asset: Asset) -> int | None:
    row = db.session.scalar(
        select(Assignment)
        .where(
            Assignment.asset_id == asset.id,
            Assignment.returned_date.is_(None),
        )
        .order_by(Assignment.assigned_date.desc())
        .limit(1),
    )
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
            f"{asset.serial_number}: {asset.name}",
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
        form = AssetEditForm(asset_id=asset.id, data=data)
    else:
        form = AssetEditForm(asset_id=asset.id, formdata=request.form)

    if form.validate_on_submit():
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

        if form.status.data == Status.ASSIGNED:
            assign_uid = int((form.assign_user_id.data or "").strip())
            _close_open_assignments(asset, today)
            db.session.add(
                Assignment(
                    asset_id=asset.id,
                    user_id=assign_uid,
                    assigned_date=today,
                    return_due_date=None,
                    returned_date=None,
                ),
            )
            _audit(
                current_user.id,
                AuditAction.ASSET_ASSIGNED,
                f"{asset.serial_number} → user id {assign_uid}",
            )
        else:
            _close_open_assignments(asset, today)

        _audit(
            current_user.id,
            AuditAction.ASSET_UPDATED,
            f"{asset.serial_number}: {asset.name}",
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

    label = f"{asset.name} ({asset.serial_number})"
    db.session.delete(asset)
    _audit(current_user.id, AuditAction.ASSET_DELETED, label)
    db.session.commit()
    flash(f"Deleted asset {label}.", "info")
    return redirect(url_for("assets.list_assets"))
