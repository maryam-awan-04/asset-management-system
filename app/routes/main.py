from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.access import standard_user_required
from app.enums import AuditAction, RequestStatus, Role, Status
from app.extensions import db
from app.forms.asset_request import AssetRequestCreateForm, AssetRequestEditNoteForm
from app.forms.empty import EmptyForm
from app.models import Asset, AssetRequest, Assignment, AuditLog

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    """Landing URL redirects to login (no separate marketing homepage)."""
    return redirect(url_for("auth.login"))


@bp.get("/dashboard")
@login_required
def dashboard():
    if current_user.role != Role.ADMIN:
        return redirect(url_for("main.my_assets"))
    return render_template("main/dashboard.html")


@bp.get("/my-assets")
@standard_user_required
def my_assets():
    rows = (
        db.session.scalars(
            select(Assignment)
            .where(
                Assignment.user_id == current_user.id,
                Assignment.returned_date.is_(None),
            )
            .options(joinedload(Assignment.asset))
            .order_by(Assignment.assigned_date.desc(), Assignment.id.desc()),
        )
        .unique()
        .all()
    )
    return render_template(
        "main/my_assets.html",
        assignments=rows,
        return_form=EmptyForm(),
    )


@bp.get("/my-assets/history")
@standard_user_required
def asset_history():
    rows = (
        db.session.scalars(
            select(Assignment)
            .where(Assignment.user_id == current_user.id)
            .options(joinedload(Assignment.asset))
            .order_by(Assignment.assigned_date.desc(), Assignment.id.desc()),
        )
        .unique()
        .all()
    )
    return render_template("main/asset_history.html", assignments=rows)


@bp.route("/my-assets/request", methods=["GET", "POST"])
@standard_user_required
def request_asset():
    form = AssetRequestCreateForm()

    if form.validate_on_submit():
        req = AssetRequest(
            user_id=current_user.id,
            asset_type=form.asset_type.data,
            status=RequestStatus.PENDING,
            note=form.note.data.strip(),
        )
        db.session.add(req)
        db.session.commit()
        flash("Request submitted to IT for review.", "success")
        return redirect(url_for("main.my_requests"))

    return render_template("main/request_asset.html", form=form)


@bp.get("/my-assets/requests")
@standard_user_required
def my_requests():
    rows = (
        db.session.scalars(
            select(AssetRequest)
            .where(AssetRequest.user_id == current_user.id)
            .options(
                joinedload(AssetRequest.asset),
                joinedload(AssetRequest.approver),
            )
            .order_by(AssetRequest.request_date.desc(), AssetRequest.id.desc())
        )
        .unique()
        .all()
    )
    return render_template("main/my_requests.html", requests=rows)


@bp.route("/my-assets/requests/<int:request_id>/edit", methods=["GET", "POST"])
@standard_user_required
def edit_my_request(request_id: int):
    req = db.session.get(AssetRequest, request_id)
    if req is None or req.user_id != current_user.id:
        flash("That request could not be found.", "warning")
        return redirect(url_for("main.my_requests"))
    if req.status != RequestStatus.PENDING:
        flash("Only pending requests can be edited.", "warning")
        return redirect(url_for("main.my_requests"))

    if request.method == "GET":
        form = AssetRequestEditNoteForm(data={"note": req.note})
    else:
        form = AssetRequestEditNoteForm(formdata=request.form)

    if form.validate_on_submit():
        req.note = form.note.data.strip()
        db.session.commit()
        flash("Request note updated.", "success")
        return redirect(url_for("main.my_requests"))

    return render_template("main/edit_request_note.html", form=form, req=req)


@bp.post("/my-assets/requests/<int:request_id>/delete")
@standard_user_required
def delete_my_request(request_id: int):
    form = EmptyForm()
    if not form.validate_on_submit():
        flash("Could not delete the request. Please try again.", "danger")
        return redirect(url_for("main.my_requests"))

    req = db.session.get(AssetRequest, request_id)
    if req is None or req.user_id != current_user.id:
        flash("That request could not be found.", "warning")
        return redirect(url_for("main.my_requests"))
    if req.status != RequestStatus.PENDING:
        flash("Only pending requests can be deleted.", "warning")
        return redirect(url_for("main.my_requests"))

    db.session.delete(req)
    db.session.commit()
    flash("Pending request deleted.", "info")
    return redirect(url_for("main.my_requests"))


@bp.post("/my-assets/<int:asset_id>/return")
@standard_user_required
def return_my_asset(asset_id: int):
    form = EmptyForm()
    if not form.validate_on_submit():
        flash("Could not record the return. Please try again.", "danger")
        return redirect(url_for("main.my_assets"))

    asset = db.session.get(Asset, asset_id)
    if asset is None:
        flash("That asset no longer exists.", "warning")
        return redirect(url_for("main.my_assets"))

    today = date.today()
    row = db.session.scalar(
        select(Assignment)
        .where(
            Assignment.asset_id == asset_id,
            Assignment.user_id == current_user.id,
            Assignment.returned_date.is_(None),
        )
        .order_by(Assignment.assigned_date.desc())
        .limit(1),
    )
    if row is None:
        flash("You do not have an active assignment for that asset.", "warning")
        return redirect(url_for("main.my_assets"))

    row.returned_date = today
    asset.status = Status.RETURNED

    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action=AuditAction.ASSET_RETURNED,
            details=(
                f"{asset.serial_number}: {asset.name} | returned by "
                f"{current_user.username} (user id {current_user.id})"
            ),
        ),
    )
    db.session.commit()
    flash(f"Return recorded for {asset.name}.", "success")
    return redirect(url_for("main.my_assets"))


@bp.get("/health")
def health():
    return jsonify(healthy=True), 200
