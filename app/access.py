"""Role-based access control decorators."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from flask import flash, redirect, url_for
from flask_login import current_user, login_required

from app.enums import Role

F = TypeVar("F", bound=Callable[..., object])


def roles_required(*roles: Role) -> Callable[[F], F]:
    """
    Require an authenticated user whose current_user.role is one of roles.
    """

    def decorator(view: F) -> F:
        @wraps(view)
        @login_required
        def wrapped_view(*args, **kwargs):
            if current_user.role not in roles:
                flash("You do not have permission to access this page.", "danger")
                if current_user.role == Role.USER:
                    return redirect(url_for("main.my_assets"))
                return redirect(url_for("main.dashboard"))
            return view(*args, **kwargs)

        return wrapped_view  # type: ignore[return-value]

    return decorator


def admin_required(view: F) -> F:
    """Shorthand for @roles_required(Role.ADMIN)."""
    return roles_required(Role.ADMIN)(view)


def standard_user_required(view: F) -> F:
    """Shorthand for @roles_required(Role.USER)."""
    return roles_required(Role.USER)(view)
