from datetime import date

from flask import jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select

from app.enums import RequestStatus, Role, Status
from app.extensions import db
from app.models import Asset, AssetRequest, Assignment
from app.routes.main.blueprint import bp


@bp.get("/")
def index():
    """Landing URL redirects to login."""
    return redirect(url_for("auth.login"))


@bp.get("/dashboard")
@login_required
def dashboard():
    if current_user.role != Role.ADMIN:
        return redirect(url_for("main.my_assets"))

    total_assets = db.session.scalar(select(func.count(Asset.id))) or 0
    available_assets = (
        db.session.scalar(
            select(func.count(Asset.id)).where(Asset.status == Status.AVAILABLE),
        )
        or 0
    )
    assigned_assets = (
        db.session.scalar(
            select(func.count(Asset.id)).where(Asset.status == Status.ASSIGNED),
        )
        or 0
    )
    assignable_pool = available_assets + assigned_assets
    utilisation_pct: float | None = (
        round((assigned_assets / assignable_pool) * 100, 1) if assignable_pool else None
    )

    overdue_assignments = (
        db.session.scalar(
            select(func.count(Assignment.id)).where(
                Assignment.returned_date.is_(None),
                Assignment.return_due_date.is_not(None),
                Assignment.return_due_date < date.today(),
            ),
        )
        or 0
    )

    total_requests = db.session.scalar(select(func.count(AssetRequest.id))) or 0
    pending_requests = (
        db.session.scalar(
            select(func.count(AssetRequest.id)).where(
                AssetRequest.status == RequestStatus.PENDING
            ),
        )
        or 0
    )

    return render_template(
        "main/dashboard.html",
        total_assets=total_assets,
        available_assets=available_assets,
        assigned_assets=assigned_assets,
        utilisation_pct=utilisation_pct,
        overdue_assignments=overdue_assignments,
        total_requests=total_requests,
        pending_requests=pending_requests,
    )


@bp.get("/health")
def health():
    return jsonify(healthy=True), 200
