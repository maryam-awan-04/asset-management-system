from datetime import date

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.access import admin_required
from app.audit import record_audit
from app.enums import AssetType, AuditAction, RequestStatus, Status
from app.extensions import db
from app.forms.empty import EmptyForm
from app.models import Asset, AssetRequest, Assignment, User
from app.routes.main.blueprint import bp
from app.util_enum import parse_enum_query_value

ASSET_NOTES_MAX_LEN = 4000


def _admin_request_review_template_kwargs(
    *,
    req: AssetRequest,
    available_assets: list[Asset],
    csrf_form: EmptyForm,
    selected_asset_id: str,
    selected_return_due: str,
    selected_asset_notes: str,
) -> dict:
    return {
        "req": req,
        "available_assets": available_assets,
        "csrf_form": csrf_form,
        "selected_asset_id": selected_asset_id,
        "selected_return_due": selected_return_due,
        "selected_asset_notes": selected_asset_notes,
        "assets_notes_by_id": {
            str(a.id): ("" if a.notes is None else str(a.notes))
            for a in available_assets
        },
    }


@bp.get("/admin/requests")
@admin_required
def admin_requests():
    stmt = select(AssetRequest).options(
        joinedload(AssetRequest.requester),
        joinedload(AssetRequest.approver),
        joinedload(AssetRequest.asset),
    )

    raw_type = request.args.get("asset_type", "").strip()
    raw_status = request.args.get("request_status", "").strip()

    asset_type_member = parse_enum_query_value(AssetType, raw_type)
    request_status_member = parse_enum_query_value(RequestStatus, raw_status)

    if asset_type_member is not None:
        stmt = stmt.where(AssetRequest.asset_type == asset_type_member)
    if request_status_member is not None:
        stmt = stmt.where(AssetRequest.status == request_status_member)

    rows = (
        db.session.scalars(
            stmt.order_by(AssetRequest.request_date.desc(), AssetRequest.id.desc())
        )
        .unique()
        .all()
    )

    return render_template(
        "main/admin_requests.html",
        requests=rows,
        filter_asset_type=asset_type_member.name if asset_type_member else "",
        filter_request_status=(
            request_status_member.name if request_status_member else ""
        ),
    )


@bp.route("/admin/requests/<int:request_id>", methods=["GET", "POST"])
@admin_required
def admin_review_request(request_id: int):
    req = db.session.get(
        AssetRequest,
        request_id,
        options=(
            joinedload(AssetRequest.requester),
            joinedload(AssetRequest.approver),
            joinedload(AssetRequest.asset),
        ),
    )
    if req is None:
        flash("That request could not be found.", "warning")
        return redirect(url_for("main.admin_requests"))

    available_assets = db.session.scalars(
        select(Asset)
        .where(
            Asset.asset_type == req.asset_type,
            Asset.status == Status.AVAILABLE,
        )
        .order_by(Asset.name.asc(), Asset.id.asc())
    ).all()

    csrf_form = EmptyForm()
    if request.method == "POST":
        if not csrf_form.validate_on_submit():
            flash("Could not process the request. Please try again.", "danger")
            return redirect(url_for("main.admin_review_request", request_id=req.id))

        if req.status != RequestStatus.PENDING:
            flash("Only pending requests can be changed.", "warning")
            return redirect(url_for("main.admin_review_request", request_id=req.id))

        action = (request.form.get("decision_action") or "").strip().lower()
        today = date.today()

        if action == "approve":
            raw_asset_id = (request.form.get("asset_id") or "").strip()
            raw_return_due = (request.form.get("return_due_date") or "").strip()
            asset_notes_raw = request.form.get("asset_notes") or ""
            if len(asset_notes_raw) > ASSET_NOTES_MAX_LEN:
                flash(
                    f"Asset notes cannot exceed {ASSET_NOTES_MAX_LEN} characters.",
                    "danger",
                )
                return render_template(
                    "main/admin_request_review.html",
                    **_admin_request_review_template_kwargs(
                        req=req,
                        available_assets=available_assets,
                        csrf_form=csrf_form,
                        selected_asset_id=raw_asset_id,
                        selected_return_due=raw_return_due,
                        selected_asset_notes=asset_notes_raw,
                    ),
                )
            return_due_date = None
            if raw_return_due:
                try:
                    return_due_date = date.fromisoformat(raw_return_due)
                except ValueError:
                    flash(
                        "Return due date must be a valid date (YYYY-MM-DD).", "danger"
                    )
                    return render_template(
                        "main/admin_request_review.html",
                        **_admin_request_review_template_kwargs(
                            req=req,
                            available_assets=available_assets,
                            csrf_form=csrf_form,
                            selected_asset_id=raw_asset_id,
                            selected_return_due=raw_return_due,
                            selected_asset_notes=asset_notes_raw,
                        ),
                    )
                if return_due_date < today:
                    flash("Return due date cannot be before today.", "danger")
                    return render_template(
                        "main/admin_request_review.html",
                        **_admin_request_review_template_kwargs(
                            req=req,
                            available_assets=available_assets,
                            csrf_form=csrf_form,
                            selected_asset_id=raw_asset_id,
                            selected_return_due=raw_return_due,
                            selected_asset_notes=asset_notes_raw,
                        ),
                    )
            if not raw_asset_id.isdigit():
                flash("Select an available asset before approving.", "danger")
                return render_template(
                    "main/admin_request_review.html",
                    **_admin_request_review_template_kwargs(
                        req=req,
                        available_assets=available_assets,
                        csrf_form=csrf_form,
                        selected_asset_id=raw_asset_id,
                        selected_return_due=raw_return_due,
                        selected_asset_notes=asset_notes_raw,
                    ),
                )

            selected_asset = db.session.get(Asset, int(raw_asset_id))
            if (
                selected_asset is None
                or selected_asset.asset_type != req.asset_type
                or selected_asset.status != Status.AVAILABLE
            ):
                flash(
                    "That asset is no longer available for this request. Please pick another one.",
                    "danger",
                )
                return redirect(url_for("main.admin_review_request", request_id=req.id))

            cleaned_notes = asset_notes_raw.strip()
            selected_asset.notes = cleaned_notes or None
            selected_asset.status = Status.ASSIGNED
            req.status = RequestStatus.APPROVED
            req.decision_date = today
            req.approved_by = current_user.id
            req.asset_id = selected_asset.id

            db.session.add(
                Assignment(
                    asset_id=selected_asset.id,
                    user_id=req.user_id,
                    assigned_date=today,
                    return_due_date=return_due_date,
                    returned_date=None,
                ),
            )

            requester = db.session.get(User, req.user_id)
            requester_name = requester.username if requester else f"user {req.user_id}"
            record_audit(
                current_user.id,
                AuditAction.ASSET_ASSIGNED,
                (
                    f"{selected_asset.serial_number}: {selected_asset.name} | assigned to "
                    f"{requester_name} via request #{req.id}"
                    f"{f'; return due {return_due_date.isoformat()}' if return_due_date else ''}"
                ),
            )

            db.session.commit()
            flash("Request approved and asset assigned.", "success")
            return redirect(url_for("main.admin_requests"))

        if action == "reject":
            requester_label = (
                req.requester.username if req.requester else f"user_id={req.user_id}"
            )
            req.status = RequestStatus.REJECTED
            req.decision_date = today
            req.approved_by = current_user.id
            req.asset_id = None
            record_audit(
                current_user.id,
                AuditAction.ASSET_REQUEST_REJECTED,
                (
                    f"Request #{req.id} | {req.asset_type.value} | "
                    f"requester {requester_label}"
                ),
            )
            db.session.commit()
            flash("Request rejected.", "info")
            return redirect(url_for("main.admin_requests"))

        flash("Invalid action.", "danger")
        return redirect(url_for("main.admin_review_request", request_id=req.id))

    return render_template(
        "main/admin_request_review.html",
        **_admin_request_review_template_kwargs(
            req=req,
            available_assets=available_assets,
            csrf_form=csrf_form,
            selected_asset_id="",
            selected_return_due="",
            selected_asset_notes="",
        ),
    )
