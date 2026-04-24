from __future__ import annotations

from enum import Enum
from typing import TypeVar

from flask import (
    Blueprint,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.access import admin_required
from app.enums import AssetType, AuditAction, Status
from app.extensions import db
from app.forms.asset import AssetCreateForm
from app.forms.empty import EmptyForm
from app.models import Asset, AuditLog

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
