from __future__ import annotations

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
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.access import admin_required
from app.audit import record_audit
from app.enums import AuditAction, Department, Role
from app.extensions import db
from app.forms.admin_user import AdminUserEditForm
from app.forms.empty import EmptyForm
from app.models import Assignment, User
from app.util_enum import parse_enum_query_value
from app.util_search import ilike_fragment_from_query

bp = Blueprint("users", __name__, url_prefix="/users")


def _snapshot_user(member: User) -> dict:
    return {
        "username": member.username,
        "role": member.role,
        "department": member.department,
    }


def _build_user_update_audit_details(before: dict, member: User) -> str:
    parts: list[str] = []
    if before["username"] != member.username:
        parts.append(f"username: {before['username']}→{member.username}")
    if before["role"] != member.role:
        parts.append(f"role: {before['role'].value}→{member.role.value}")
    if before["department"] != member.department:
        parts.append(
            f"department: {before['department'].value}→{member.department.value}",
        )
    inner = "; ".join(parts) if parts else "no field changes"
    return f"user id {member.id} ({member.email}) | {inner}"


def _other_admin_count(exclude_user_id: int) -> int:
    return (
        db.session.scalar(
            select(func.count(User.id)).where(
                User.role == Role.ADMIN, User.id != exclude_user_id
            ),
        )
        or 0
    )


def _filtered_users_bundle(
    raw_dept: str,
    raw_role: str,
    q_raw: str,
) -> tuple[list[User], str, str, str]:
    stmt = select(User)

    q_stripped = (q_raw or "").strip()

    dept_member = parse_enum_query_value(Department, raw_dept)
    role_member = parse_enum_query_value(Role, raw_role)

    dept_key = dept_member.name if dept_member is not None else ""
    role_key = role_member.name if role_member is not None else ""

    if dept_member is not None:
        stmt = stmt.where(User.department == dept_member)
    if role_member is not None:
        stmt = stmt.where(User.role == role_member)

    q_safe = ilike_fragment_from_query(q_stripped)
    if q_safe is not None:
        stmt = stmt.where(User.username.ilike(f"%{q_safe}%"))

    stmt = stmt.order_by(User.id.asc())
    users = db.session.scalars(stmt).all()
    return users, dept_key, role_key, q_stripped


@bp.get("/")
@admin_required
def list_users():
    users, dept_key, role_key, q_stripped = _filtered_users_bundle(
        request.args.get("department", ""),
        request.args.get("role", ""),
        request.args.get("q") or "",
    )

    html = render_template(
        "users/list.html",
        users=users,
        filter_department=dept_key,
        filter_role=role_key,
        filter_q=q_stripped,
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@bp.get("/list-results")
@admin_required
def list_users_results():
    users, dept_key, role_key, q_stripped = _filtered_users_bundle(
        request.args.get("department", ""),
        request.args.get("role", ""),
        request.args.get("q") or "",
    )
    html = render_template(
        "users/_list_results.html",
        users=users,
        filter_department=dept_key,
        filter_role=role_key,
        filter_q=q_stripped,
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@bp.get("/<int:user_id>/assets")
@admin_required
def view_user_assets(user_id: int):
    member = db.session.get(User, user_id)
    if member is None:
        flash("That user could not be found.", "warning")
        return redirect(url_for("users.list_users"))

    rows = (
        db.session.scalars(
            select(Assignment)
            .where(Assignment.user_id == user_id)
            .options(joinedload(Assignment.asset))
            .order_by(Assignment.assigned_date.desc(), Assignment.id.desc()),
        )
        .unique()
        .all()
    )

    current_assignments = [r for r in rows if r.returned_date is None]
    past_assignments = [r for r in rows if r.returned_date is not None]

    html = render_template(
        "users/user_assets.html",
        member=member,
        current_assignments=current_assignments,
        past_assignments=past_assignments,
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id: int):
    member = db.session.get(User, user_id)
    if member is None:
        flash("That user could not be found.", "warning")
        return redirect(url_for("users.list_users"))

    if request.method == "GET":
        form = AdminUserEditForm(
            exclude_user_id=member.id,
            data={
                "username": member.username,
                "role": member.role.name,
                "department": member.department.name,
            },
        )
    else:
        form = AdminUserEditForm(exclude_user_id=member.id, formdata=request.form)

    if form.validate_on_submit():
        if member.id == current_user.id and form.role.data != Role.ADMIN:
            if _other_admin_count(member.id) == 0:
                flash(
                    "You cannot remove your own administrator role while you are the only admin.",
                    "danger",
                )
                return render_template("users/edit.html", form=form, member=member)

        before = _snapshot_user(member)
        member.username = form.username.data
        member.role = form.role.data
        member.department = form.department.data
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            flash("Could not save. That username may already be in use.", "danger")
            return render_template("users/edit.html", form=form, member=member)

        record_audit(
            current_user.id,
            AuditAction.USER_UPDATED,
            _build_user_update_audit_details(before, member),
        )
        db.session.commit()
        flash(f"User updated. ID: {member.id}.", "success")
        return redirect(url_for("users.list_users"))

    return render_template("users/edit.html", form=form, member=member)


@bp.post("/<int:user_id>/delete")
@admin_required
def delete_user(user_id: int):
    form = EmptyForm()
    if not form.validate_on_submit():
        flash("Could not delete the user. Please try again.", "danger")
        return redirect(url_for("users.list_users"))

    member = db.session.get(User, user_id)
    if member is None:
        flash("That user no longer exists.", "warning")
        return redirect(url_for("users.list_users"))

    if member.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("users.list_users"))

    open_assignments = (
        db.session.scalar(
            select(func.count(Assignment.id)).where(
                Assignment.user_id == member.id,
                Assignment.returned_date.is_(None),
            ),
        )
        or 0
    )
    if open_assignments > 0:
        flash(
            "Cannot delete this user while they have assets assigned.",
            "danger",
        )
        return redirect(url_for("users.list_users"))

    if member.role == Role.ADMIN:
        admin_total = (
            db.session.scalar(
                select(func.count(User.id)).where(User.role == Role.ADMIN)
            )
            or 0
        )
        if admin_total <= 1:
            flash("Cannot delete the only administrator account.", "danger")
            return redirect(url_for("users.list_users"))

    label = f"{member.username} ({member.email})"
    db.session.delete(member)
    record_audit(current_user.id, AuditAction.USER_DELETED, label)
    db.session.commit()
    flash(f"Deleted user {label}.", "info")
    return redirect(url_for("users.list_users"))
