from datetime import date

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.access import admin_required
from app.audit import record_audit
from app.enums import AssetType, AuditAction, RequestStatus, Status
from app.extensions import db
from app.forms.admin_request_review import AdminRequestReviewForm
from app.models import Asset, AssetRequest, Assignment, User
from app.routes.main.blueprint import bp
from app.util_enum import parse_enum_query_value


def _admin_request_review_template_kwargs(
    *,
    req: AssetRequest,
    available_assets: list[Asset],
    review_form: AdminRequestReviewForm,
) -> dict:
    return {
        "req": req,
        "available_assets": available_assets,
        "review_form": review_form,
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

    radio_choices = [
        (str(a.id), f"{a.name} — {a.serial_number}") for a in available_assets
    ]

    if request.method == "POST":
        review_form = AdminRequestReviewForm(
            formdata=request.form,
            asset_radio_choices=radio_choices,
        )
        if req.status != RequestStatus.PENDING:
            flash("Only pending requests can be changed.", "warning")
            return redirect(url_for("main.admin_review_request", request_id=req.id))

        if not review_form.validate():
            return render_template(
                "main/admin_request_review.html",
                **_admin_request_review_template_kwargs(
                    req=req,
                    available_assets=available_assets,
                    review_form=review_form,
                ),
            )

        today = date.today()

        if review_form.reject.data:
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

        if review_form.approve.data:
            if not available_assets:
                flash(
                    "There are no available assets of this type right now.",
                    "danger",
                )
                return redirect(url_for("main.admin_review_request", request_id=req.id))

            raw_asset_id = str(review_form.asset_id.data or "")
            if not raw_asset_id.isdigit():
                flash("Select an available asset before approving.", "danger")
                return render_template(
                    "main/admin_request_review.html",
                    **_admin_request_review_template_kwargs(
                        req=req,
                        available_assets=available_assets,
                        review_form=review_form,
                    ),
                )

            return_due_date = review_form.return_due_date.data
            asset_notes_raw = review_form.asset_notes.data or ""

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
                AuditAction.ASSET_REQUEST_APPROVED,
                (
                    f"Request #{req.id} | {req.asset_type.value} | "
                    f"requester {requester_name} | asset "
                    f"{selected_asset.serial_number}: {selected_asset.name}"
                    f"{f' | return due {return_due_date.isoformat()}' if return_due_date else ''}"
                ),
            )
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

        flash("Invalid action.", "danger")
        return redirect(url_for("main.admin_review_request", request_id=req.id))

    review_form = AdminRequestReviewForm(asset_radio_choices=radio_choices)
    return render_template(
        "main/admin_request_review.html",
        **_admin_request_review_template_kwargs(
            req=req,
            available_assets=available_assets,
            review_form=review_form,
        ),
    )
