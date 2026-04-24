"""Development-only data seeding."""

from __future__ import annotations

import os
from datetime import date

from sqlalchemy import select

from app.enums import AssetType, Department, Role, Status
from app.extensions import db
from app.models import Asset, User
from app.passwords import hash_password

LOCALDEV_USERNAME = "localdev"
LOCALDEV_EMAIL = "localdev@gmail.com"


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


DEMO_ASSET_SERIAL_PREFIX = "SN-DEMO-"


def ensure_demo_assets() -> None:
    """
    Insert sample assets for local UI testing (skipped if SN-DEMO-001 already exists).
    """
    if db.session.scalar(
        select(Asset).filter_by(serial_number=f"{DEMO_ASSET_SERIAL_PREFIX}001"),
    ):
        return

    today = date.today()
    samples: list[Asset] = [
        Asset(
            name="MacBook Pro 14",
            asset_type=AssetType.LAPTOP,
            serial_number=f"{DEMO_ASSET_SERIAL_PREFIX}001",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 3, 1),
            expiry_date=None,
            notes="Engineering pool laptop.",
        ),
        Asset(
            name="Dell UltraSharp 27",
            asset_type=AssetType.MONITOR,
            serial_number=f"{DEMO_ASSET_SERIAL_PREFIX}002",
            status=Status.ASSIGNED,
            purchase_date=date(2023, 11, 15),
            expiry_date=None,
            notes="Desk bundle A3.",
        ),
        Asset(
            name="Logitech MX Keys",
            asset_type=AssetType.KEYBOARD,
            serial_number=f"{DEMO_ASSET_SERIAL_PREFIX}003",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 1, 10),
            expiry_date=None,
            notes=None,
        ),
        Asset(
            name="Microsoft 365 E5",
            asset_type=AssetType.LICENSE,
            serial_number=f"{DEMO_ASSET_SERIAL_PREFIX}004",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 6, 1),
            expiry_date=date(today.year + 1, 5, 31),
            notes="Annual subscription seat.",
        ),
        Asset(
            name="Poly Voyager Focus 2",
            asset_type=AssetType.HEADPHONES,
            serial_number=f"{DEMO_ASSET_SERIAL_PREFIX}005",
            status=Status.UNDER_MAINTENANCE,
            purchase_date=date(2022, 8, 20),
            expiry_date=None,
            notes="Left ear cushion replacement.",
        ),
        Asset(
            name="Meeting Owl 3",
            asset_type=AssetType.WEBCAM,
            serial_number=f"{DEMO_ASSET_SERIAL_PREFIX}006",
            status=Status.RETIRED,
            purchase_date=date(2021, 4, 1),
            expiry_date=None,
            notes="Replaced under refresh policy.",
        ),
        Asset(
            name="Logitech MX Master 3S",
            asset_type=AssetType.MOUSE,
            serial_number=f"{DEMO_ASSET_SERIAL_PREFIX}007",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 2, 28),
            expiry_date=None,
            notes=None,
        ),
        Asset(
            name="Jabra Evolve2 65",
            asset_type=AssetType.HEADPHONES,
            serial_number=f"{DEMO_ASSET_SERIAL_PREFIX}008",
            status=Status.AVAILABLE,
            purchase_date=date(2023, 9, 5),
            expiry_date=None,
            notes="UC-certified headset.",
        ),
    ]
    db.session.add_all(samples)
    db.session.commit()
