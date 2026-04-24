from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_, select

from app.enums import AuditAction, Role
from app.extensions import db
from app.forms.auth import LoginForm, RegistrationForm
from app.models import AuditLog, User
from app.passwords import hash_password, passwords_match

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _audit(
    user_id: int | None, action: AuditAction, details: str | None = None
) -> None:
    db.session.add(
        AuditLog(user_id=user_id, action=action, details=details),
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        user = db.session.scalar(select(User).filter_by(username=username))

        if not user or not passwords_match(user.password_hash, form.password.data):
            flash(
                "Invalid username or password.",
                "danger",
            )
            _audit(None, AuditAction.LOGIN_FAILED, None)
            db.session.commit()
            return render_template("auth/login.html", form=form)

        session.permanent = True
        login_user(user, remember=form.remember_me.data)
        flash("You are signed in.", "success")
        _audit(user.id, AuditAction.LOGIN_SUCCESS, None)
        db.session.commit()

        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        email_norm = form.email.data.strip().lower()
        exists = db.session.scalar(
            select(User).where(
                or_(
                    User.username == form.username.data.strip(),
                    User.email == email_norm,
                ),
            ),
        )
        if exists:
            flash(
                "Registration failed. Please try a different username or email.",
                "danger",
            )
            return render_template("auth/register.html", form=form)

        user = User(
            username=form.username.data.strip(),
            email=email_norm,
            password_hash=hash_password(form.password.data),
            role=Role.USER,
            department=form.department.data,
        )
        db.session.add(user)
        db.session.flush()
        _audit(user.id, AuditAction.USER_CREATED, "Self-registration")
        db.session.commit()

        flash("Your account has been created. Please sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
