"""Ensure the local development admin account exists."""

from __future__ import annotations

import os

from sqlalchemy import select

from app.enums import Department, Role
from app.extensions import db
from app.models import User
from app.passwords import hash_password
from app.seed.constants import LOCALDEV_EMAIL, LOCALDEV_USERNAME


def ensure_localdev_admin() -> None:
    """
    Fixed admin account for local testing.

    Username localdev, email localdev@gmail.com, role admin.
    Password: LOCALDEV_ADMIN_PASSWORD env var, or default LocalDev1!
    """
    password = os.environ.get("LOCALDEV_ADMIN_PASSWORD", "LocalDev1!")
    pw_hash = hash_password(password)

    other = db.session.scalar(
        select(User).where(
            User.email == LOCALDEV_EMAIL,
            User.username != LOCALDEV_USERNAME,
        ),
    )
    if other is not None:
        return

    user = db.session.scalar(select(User).filter_by(username=LOCALDEV_USERNAME))
    if user is None:
        db.session.add(
            User(
                username=LOCALDEV_USERNAME,
                email=LOCALDEV_EMAIL,
                password_hash=pw_hash,
                role=Role.ADMIN,
                department=Department.TECHNOLOGY,
            ),
        )
    else:
        user.email = LOCALDEV_EMAIL
        user.role = Role.ADMIN
        user.password_hash = pw_hash

    db.session.commit()
