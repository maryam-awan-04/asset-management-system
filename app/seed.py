"""Development-only data seeding."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.enums import AssetType, AuditAction, Department, Role, Status
from app.extensions import db
from app.models import Asset, Assignment, AuditLog, User
from app.passwords import hash_password

LOCALDEV_USERNAME = "localdev"
LOCALDEV_EMAIL = "localdev@gmail.com"

SEED_SERIAL_MARKER = "SEED-SN-00001"
SEED_USER_PASSWORD = os.environ.get("SEED_USER_PASSWORD", "SeedDemo1!")


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


def ensure_demo_assets() -> None:
    """
    Insert sample assets for local UI testing.
    """
    if db.session.scalar(select(Asset).filter_by(serial_number=SEED_SERIAL_MARKER)):
        return

    admin = db.session.scalar(select(User).filter_by(username=LOCALDEV_USERNAME))
    if admin is None:
        return

    actor_id = admin.id
    pw_hash = hash_password(SEED_USER_PASSWORD)
    today = date.today()

    seed_users_spec: list[tuple[str, str, Department, Role]] = [
        ("anna.clark", "anna.clark@seed.company.example", Department.CP, Role.USER),
        ("ben.otoole", "ben.otoole@seed.company.example", Department.STS, Role.USER),
        ("chen.wei", "chen.wei@seed.company.example", Department.TECHNOLOGY, Role.USER),
        (
            "divya.nair",
            "divya.nair@seed.company.example",
            Department.FINANCE,
            Role.USER,
        ),
        (
            "elena.rossi",
            "elena.rossi@seed.company.example",
            Department.LEGAL,
            Role.USER,
        ),
        ("felix.hahn", "felix.hahn@seed.company.example", Department.HR, Role.USER),
        (
            "grace.park",
            "grace.park@seed.company.example",
            Department.TECHNOLOGY,
            Role.USER,
        ),
        ("hector.mora", "hector.mora@seed.company.example", Department.CP, Role.USER),
        ("indira.shah", "indira.shah@seed.company.example", Department.STS, Role.USER),
        (
            "james.reef",
            "james.reef@seed.company.example",
            Department.TECHNOLOGY,
            Role.USER,
        ),
    ]

    users: list[User] = [
        User(
            username=username,
            email=email,
            password_hash=pw_hash,
            role=role,
            department=dept,
        )
        for username, email, dept, role in seed_users_spec
    ]
    db.session.add_all(users)
    db.session.flush()

    by_username = {u.username: u for u in users}

    assets: list[Asset] = [
        Asset(
            name="MacBook Pro 16 (Finance pool)",
            asset_type=AssetType.LAPTOP,
            serial_number="SEED-SN-00001",
            status=Status.ASSIGNED,
            purchase_date=date(2024, 2, 10),
            expiry_date=None,
            notes="Primary laptop for finance analysts.",
        ),
        Asset(
            name="Dell UltraSharp 32",
            asset_type=AssetType.MONITOR,
            serial_number="SEED-SN-00002",
            status=Status.ASSIGNED,
            purchase_date=date(2023, 9, 1),
            expiry_date=None,
            notes="STS trading floor desk B12.",
        ),
        Asset(
            name="Logitech MX Keys S",
            asset_type=AssetType.KEYBOARD,
            serial_number="SEED-SN-00003",
            status=Status.ASSIGNED,
            purchase_date=date(2024, 5, 20),
            expiry_date=None,
            notes="Paired with hot-desk dock 4.",
        ),
        Asset(
            name="Microsoft 365 E5 (seat)",
            asset_type=AssetType.LICENSE,
            serial_number="SEED-SN-00004",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 1, 1),
            expiry_date=date(today.year + 1, 12, 31),
            notes="Unassigned seat; assign during onboarding.",
        ),
        Asset(
            name="Jabra Evolve2 75",
            asset_type=AssetType.HEADPHONES,
            serial_number="SEED-SN-00005",
            status=Status.AVAILABLE,
            purchase_date=date(2023, 6, 15),
            expiry_date=None,
            notes="Returned from contractor; inspected OK.",
        ),
        Asset(
            name="Logitech MX Master 3S",
            asset_type=AssetType.MOUSE,
            serial_number="SEED-SN-00006",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 3, 8),
            expiry_date=None,
            notes="Spares cupboard — Technology.",
        ),
        Asset(
            name="Shure MV7 USB mic",
            asset_type=AssetType.MICROPHONE,
            serial_number="SEED-SN-00007",
            status=Status.UNDER_MAINTENANCE,
            purchase_date=date(2022, 11, 1),
            expiry_date=None,
            notes="USB port intermittent; with vendor RMA.",
        ),
        Asset(
            name="Poly Studio P15",
            asset_type=AssetType.WEBCAM,
            serial_number="SEED-SN-00008",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 4, 22),
            expiry_date=None,
            notes="Legal videoconference kit.",
        ),
        Asset(
            name="Lenovo ThinkPad P1",
            asset_type=AssetType.LAPTOP,
            serial_number="SEED-SN-00009",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 7, 1),
            expiry_date=None,
            notes="Heavy workstation for CAD pilots.",
        ),
        Asset(
            name="Dell Pro 24 Monitor",
            asset_type=AssetType.MONITOR,
            serial_number="SEED-SN-00010",
            status=Status.RETIRED,
            purchase_date=date(2019, 4, 10),
            expiry_date=None,
            notes="End of life; kept for parts.",
        ),
        Asset(
            name="Apple Magic Trackpad",
            asset_type=AssetType.MOUSE,
            serial_number="SEED-SN-00011",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 8, 5),
            expiry_date=None,
            notes="HR ergonomics trial stock.",
        ),
        Asset(
            name="Adobe Creative Cloud (named user)",
            asset_type=AssetType.LICENSE,
            serial_number="SEED-SN-00012",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 6, 1),
            expiry_date=date(today.year, 5, 31),
            notes="CP marketing shared licence (not yet assigned).",
        ),
    ]
    db.session.add_all(assets)
    db.session.flush()

    by_serial = {a.serial_number: a for a in assets}

    anna = by_username["anna.clark"]
    ben = by_username["ben.otoole"]
    chen = by_username["chen.wei"]
    divya = by_username["divya.nair"]

    assign_day_active = today - timedelta(days=14)
    assign_day_returned = today - timedelta(days=60)
    return_day = today - timedelta(days=7)

    assignments: list[Assignment] = [
        Assignment(
            asset_id=by_serial["SEED-SN-00001"].id,
            user_id=anna.id,
            assigned_date=assign_day_active,
            return_due_date=None,
            returned_date=None,
        ),
        Assignment(
            asset_id=by_serial["SEED-SN-00002"].id,
            user_id=ben.id,
            assigned_date=assign_day_active,
            return_due_date=None,
            returned_date=None,
        ),
        Assignment(
            asset_id=by_serial["SEED-SN-00003"].id,
            user_id=chen.id,
            assigned_date=assign_day_active,
            return_due_date=None,
            returned_date=None,
        ),
        Assignment(
            asset_id=by_serial["SEED-SN-00005"].id,
            user_id=divya.id,
            assigned_date=assign_day_returned,
            return_due_date=None,
            returned_date=return_day,
        ),
    ]
    db.session.add_all(assignments)

    base = datetime.now(timezone.utc) - timedelta(days=50)
    logs: list[AuditLog] = []

    def log(ts: datetime, action: AuditAction, details: str) -> None:
        logs.append(
            AuditLog(user_id=actor_id, action=action, details=details, timestamp=ts)
        )

    t = base
    for u in users:
        log(
            t,
            AuditAction.USER_CREATED,
            f"Seeded demo user | {u.username} ({u.email}) | {u.department.value}; {u.role.value}",
        )
        t += timedelta(minutes=2)

    t = base + timedelta(days=1)
    for a in assets:
        log(
            t,
            AuditAction.ASSET_CREATED,
            f"{a.serial_number}: {a.name} | created as {a.asset_type.value}; status {a.status.value}",
        )
        t += timedelta(minutes=5)

    t_assign = base + timedelta(days=20)
    laptop = by_serial["SEED-SN-00001"]
    monitor = by_serial["SEED-SN-00002"]
    keyboard = by_serial["SEED-SN-00003"]
    headset = by_serial["SEED-SN-00005"]

    log(
        t_assign,
        AuditAction.ASSET_ASSIGNED,
        f"{laptop.serial_number}: {laptop.name} | assigned to {anna.username} (user id {anna.id})",
    )
    log(
        t_assign + timedelta(minutes=10),
        AuditAction.ASSET_ASSIGNED,
        f"{monitor.serial_number}: {monitor.name} | assigned to {ben.username} (user id {ben.id})",
    )
    log(
        t_assign + timedelta(minutes=20),
        AuditAction.ASSET_ASSIGNED,
        f"{keyboard.serial_number}: {keyboard.name} | assigned to {chen.username} (user id {chen.id})",
    )

    t_old = base + timedelta(days=10)
    log(
        t_old,
        AuditAction.ASSET_ASSIGNED,
        f"{headset.serial_number}: {headset.name} | assigned to {divya.username} (user id {divya.id})",
    )
    log(
        base + timedelta(days=35),
        AuditAction.ASSET_RETURNED,
        f"{headset.serial_number}: {headset.name} | returned by {divya.username} (user id {divya.id}); back to pool",
    )

    log(
        base + timedelta(days=40),
        AuditAction.ASSET_UPDATED,
        f"{headset.serial_number}: {headset.name} | status: Assigned→Available",
    )

    log(
        base + timedelta(days=41),
        AuditAction.LOGIN_SUCCESS,
        f"{LOCALDEV_USERNAME} | post-seed verification login (demo)",
    )

    db.session.add_all(logs)
    db.session.commit()
