from __future__ import annotations

from enum import Enum
from typing import TypeVar

from flask import Blueprint, make_response, render_template, request
from sqlalchemy import select

from app.access import admin_required
from app.enums import AssetType, Status
from app.extensions import db
from app.models import Asset

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
