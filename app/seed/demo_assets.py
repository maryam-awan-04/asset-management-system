from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.enums import AssetType, AuditAction, Department, Role, Status
from app.extensions import db
from app.models import Asset, Assignment, AuditLog, User
from app.passwords import hash_password
from app.seed.constants import (
    LOCALDEV_USERNAME,
    SEED_EMAIL_DOMAIN,
    SEED_SERIAL_MARKER,
    SEED_USER_PASSWORD,
)
from app.seed.overdue_requests import seed_overdue_and_requests


def ensure_demo_assets() -> None:
    """
    Insert realistic sample users, assets, assignments, and audit history for local UI testing.
    """
    existing_seed_assets = db.session.scalar(
        select(Asset).filter_by(serial_number=SEED_SERIAL_MARKER),
    )
    if existing_seed_assets:
        admin_existing = db.session.scalar(
            select(User).filter_by(username=LOCALDEV_USERNAME)
        )
        if admin_existing is not None:
            seed_overdue_and_requests(admin=admin_existing, today=date.today())
            db.session.commit()
        return

    admin = db.session.scalar(select(User).filter_by(username=LOCALDEV_USERNAME))
    if admin is None:
        return

    actor_id = admin.id
    pw_hash = hash_password(SEED_USER_PASSWORD)
    today = date.today()

    seed_users_spec: list[tuple[str, str, Department, Role]] = [
        (
            "sarah.mitchell",
            f"sarah.mitchell@{SEED_EMAIL_DOMAIN}",
            Department.FINANCE,
            Role.USER,
        ),
        (
            "david.nguyen",
            f"david.nguyen@{SEED_EMAIL_DOMAIN}",
            Department.STS,
            Role.USER,
        ),
        (
            "emily.carter",
            f"emily.carter@{SEED_EMAIL_DOMAIN}",
            Department.TECHNOLOGY,
            Role.USER,
        ),
        (
            "james.okonkwo",
            f"james.okonkwo@{SEED_EMAIL_DOMAIN}",
            Department.FINANCE,
            Role.USER,
        ),
        (
            "priya.sharma",
            f"priya.sharma@{SEED_EMAIL_DOMAIN}",
            Department.LEGAL,
            Role.USER,
        ),
        ("marcus.weber", f"marcus.weber@{SEED_EMAIL_DOMAIN}", Department.HR, Role.USER),
        (
            "olivia.brooks",
            f"olivia.brooks@{SEED_EMAIL_DOMAIN}",
            Department.TECHNOLOGY,
            Role.USER,
        ),
        (
            "danielle.price",
            f"danielle.price@{SEED_EMAIL_DOMAIN}",
            Department.CP,
            Role.USER,
        ),
        ("ryan.cooper", f"ryan.cooper@{SEED_EMAIL_DOMAIN}", Department.STS, Role.USER),
        (
            "keiko.tanaka",
            f"keiko.tanaka@{SEED_EMAIL_DOMAIN}",
            Department.TECHNOLOGY,
            Role.USER,
        ),
        (
            "amelia.jones",
            f"amelia.jones@{SEED_EMAIL_DOMAIN}",
            Department.FINANCE,
            Role.USER,
        ),
        (
            "liam.oconnor",
            f"liam.oconnor@{SEED_EMAIL_DOMAIN}",
            Department.LEGAL,
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
    sarah = by_username["sarah.mitchell"]
    david = by_username["david.nguyen"]
    emily = by_username["emily.carter"]
    james = by_username["james.okonkwo"]
    olivia = by_username["olivia.brooks"]
    ryan = by_username["ryan.cooper"]

    assign_recent = today - timedelta(days=18)
    assign_old = today - timedelta(days=72)
    return_headset = today - timedelta(days=11)

    assets: list[Asset] = [
        Asset(
            name='Apple MacBook Pro 16" (M3 Pro, 36GB)',
            asset_type=AssetType.LAPTOP,
            serial_number="IT-LP-24-00891",
            status=Status.ASSIGNED,
            purchase_date=date(2024, 3, 12),
            expiry_date=None,
            notes="Corporate finance pool â€” primary analyst build.",
        ),
        Asset(
            name="Lenovo ThinkPad P1 Gen 6 (RTX 4070)",
            asset_type=AssetType.LAPTOP,
            serial_number="LEN-PF4ZK9Q2",
            status=Status.ASSIGNED,
            purchase_date=date(2024, 8, 2),
            expiry_date=None,
            notes="Heavy workstation for modelling and data science.",
        ),
        Asset(
            name='Dell UltraSharp U3223QE (32" 4K)',
            asset_type=AssetType.MONITOR,
            serial_number="DELL-U3223QE-4KQ2N1",
            status=Status.ASSIGNED,
            purchase_date=date(2023, 11, 5),
            expiry_date=None,
            notes="STS trading floor â€” desk cluster T-14.",
        ),
        Asset(
            name='Dell Pro 27" P2723DE',
            asset_type=AssetType.MONITOR,
            serial_number="DELL-P2723DE-8MZ3K9",
            status=Status.ASSIGNED,
            purchase_date=date(2024, 1, 18),
            expiry_date=None,
            notes="STS operations â€” second screen for shift lead.",
        ),
        Asset(
            name="Logitech MX Keys S (Graphite)",
            asset_type=AssetType.KEYBOARD,
            serial_number="LOG-MXK-BKEY-00221",
            status=Status.ASSIGNED,
            purchase_date=date(2024, 5, 9),
            expiry_date=None,
            notes="Technology hot-dock â€” paired with TB4 dock 7.",
        ),
        Asset(
            name='Apple MacBook Air 13" (M2, returned)',
            asset_type=AssetType.LAPTOP,
            serial_number="APL-FVFK71Q9Q05D",
            status=Status.RETURNED,
            purchase_date=date(2023, 6, 20),
            expiry_date=None,
            notes="Awaiting secure wipe before reassignment.",
        ),
        Asset(
            name='Microsoft Surface Laptop 5 (15")',
            asset_type=AssetType.LAPTOP,
            serial_number="MSFT-SL5-9K2M4410",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 9, 1),
            expiry_date=None,
            notes="Spare pool â€” Legal / exec loaner.",
        ),
        Asset(
            name='Dell UltraSharp U2424H (24")',
            asset_type=AssetType.MONITOR,
            serial_number="DELL-U2424H-3N8KQ7",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 4, 22),
            expiry_date=None,
            notes="Unboxed spare â€” Customer & Products marketing.",
        ),
        Asset(
            name="Logitech MX Master 3S (Pale Grey)",
            asset_type=AssetType.MOUSE,
            serial_number="LOG-MXM3S-11K882",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 3, 14),
            expiry_date=None,
            notes="Spares cupboard â€” Technology.",
        ),
        Asset(
            name="Logitech MX Anywhere 3S",
            asset_type=AssetType.MOUSE,
            serial_number="LOG-MXA3S-44B901",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 7, 30),
            expiry_date=None,
            notes="Travel kit stock â€” Finance.",
        ),
        Asset(
            name="Jabra Evolve2 75 UC (Stereo)",
            asset_type=AssetType.HEADPHONES,
            serial_number="JBR-EV275-QP93L2",
            status=Status.AVAILABLE,
            purchase_date=date(2023, 10, 2),
            expiry_date=None,
            notes="Returned from contractor â€” inspected, ready to reissue.",
        ),
        Asset(
            name="Poly Studio P15 (Personal video bar)",
            asset_type=AssetType.WEBCAM,
            serial_number="POL-P15-UK90M1",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 2, 27),
            expiry_date=None,
            notes="Legal videoconference kit â€” unassigned.",
        ),
        Asset(
            name="Elgato Facecam Pro",
            asset_type=AssetType.WEBCAM,
            serial_number="ELG-FCPRO-7HX22",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 6, 11),
            expiry_date=None,
            notes="Streaming / comms trial stock.",
        ),
        Asset(
            name="Shure MV7 USB/XLR (Black)",
            asset_type=AssetType.MICROPHONE,
            serial_number="SHR-MV7-USB-44102",
            status=Status.UNDER_MAINTENANCE,
            purchase_date=date(2022, 12, 4),
            expiry_date=None,
            notes="USB-C intermittent â€” with vendor RMA.",
        ),
        Asset(
            name="Microsoft 365 E5 (per-user subscription)",
            asset_type=AssetType.LICENSE,
            serial_number="MSFT-M365-E5-SN8841201",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 1, 1),
            expiry_date=date(today.year + 1, 12, 31),
            notes="Unassigned seat â€” provision during onboarding.",
        ),
        Asset(
            name="Adobe Creative Cloud (named user, annual)",
            asset_type=AssetType.LICENSE,
            serial_number="ADOBE-CC-TM-2025-77102",
            status=Status.AVAILABLE,
            purchase_date=date(2025, 1, 15),
            expiry_date=date(today.year, 12, 31),
            notes="Marketing shared licence â€” not yet assigned.",
        ),
        Asset(
            name='Dell Pro 24" P2422H (EOL)',
            asset_type=AssetType.MONITOR,
            serial_number="DELL-P2422H-EOL-1993",
            status=Status.RETIRED,
            purchase_date=date(2018, 5, 4),
            expiry_date=None,
            notes="Retired â€” kept for parts only.",
        ),
        Asset(
            name="Keychron Q6 Pro (100%, tactile)",
            asset_type=AssetType.KEYBOARD,
            serial_number="KEY-Q6PRO-BK88",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 10, 8),
            expiry_date=None,
            notes="HR ergonomics trial â€” surplus after pilot.",
        ),
    ]

    db.session.add_all(assets)
    db.session.flush()

    by_serial = {a.serial_number: a for a in assets}

    assignments: list[Assignment] = [
        Assignment(
            asset_id=by_serial["IT-LP-24-00891"].id,
            user_id=sarah.id,
            assigned_date=assign_recent,
            return_due_date=today - timedelta(days=9),
            returned_date=None,
        ),
        Assignment(
            asset_id=by_serial["LEN-PF4ZK9Q2"].id,
            user_id=james.id,
            assigned_date=assign_recent,
            return_due_date=today + timedelta(days=14),
            returned_date=None,
        ),
        Assignment(
            asset_id=by_serial["DELL-U3223QE-4KQ2N1"].id,
            user_id=david.id,
            assigned_date=assign_recent,
            return_due_date=today - timedelta(days=5),
            returned_date=None,
        ),
        Assignment(
            asset_id=by_serial["DELL-P2723DE-8MZ3K9"].id,
            user_id=ryan.id,
            assigned_date=assign_recent,
            return_due_date=today + timedelta(days=30),
            returned_date=None,
        ),
        Assignment(
            asset_id=by_serial["LOG-MXK-BKEY-00221"].id,
            user_id=emily.id,
            assigned_date=assign_recent,
            return_due_date=None,
            returned_date=None,
        ),
        Assignment(
            asset_id=by_serial["JBR-EV275-QP93L2"].id,
            user_id=olivia.id,
            assigned_date=assign_old,
            return_due_date=None,
            returned_date=return_headset,
        ),
        Assignment(
            asset_id=by_serial["APL-FVFK71Q9Q05D"].id,
            user_id=olivia.id,
            assigned_date=assign_old - timedelta(days=40),
            return_due_date=None,
            returned_date=assign_old - timedelta(days=5),
        ),
    ]
    db.session.add_all(assignments)

    seed_overdue_and_requests(admin=admin, today=today)

    base = datetime.now(timezone.utc) - timedelta(days=55)
    logs: list[AuditLog] = []

    def log(ts: datetime, action: AuditAction, details: str) -> None:
        logs.append(
            AuditLog(user_id=actor_id, action=action, details=details, timestamp=ts),
        )

    t = base
    for u in users:
        log(
            t,
            AuditAction.USER_CREATED,
            f"User created | {u.username} ({u.email}) | {u.department.value}; {u.role.value}",
        )
        t += timedelta(minutes=2)

    t = base + timedelta(days=1)
    for a in assets:
        log(
            t,
            AuditAction.ASSET_CREATED,
            f"{a.serial_number}: {a.name} | {a.asset_type.value}; status {a.status.value}",
        )
        t += timedelta(minutes=4)

    t_assign = base + timedelta(days=18)
    log(
        t_assign,
        AuditAction.ASSET_ASSIGNED,
        f"{by_serial['IT-LP-24-00891'].serial_number}: {by_serial['IT-LP-24-00891'].name} | "
        f"assigned to {sarah.username} (user id {sarah.id})",
    )
    log(
        t_assign + timedelta(minutes=8),
        AuditAction.ASSET_ASSIGNED,
        f"{by_serial['LEN-PF4ZK9Q2'].serial_number}: {by_serial['LEN-PF4ZK9Q2'].name} | "
        f"assigned to {james.username} (user id {james.id})",
    )
    log(
        t_assign + timedelta(minutes=16),
        AuditAction.ASSET_ASSIGNED,
        f"{by_serial['DELL-U3223QE-4KQ2N1'].serial_number}: {by_serial['DELL-U3223QE-4KQ2N1'].name} | "
        f"assigned to {david.username} (user id {david.id})",
    )
    log(
        t_assign + timedelta(minutes=24),
        AuditAction.ASSET_ASSIGNED,
        f"{by_serial['DELL-P2723DE-8MZ3K9'].serial_number}: {by_serial['DELL-P2723DE-8MZ3K9'].name} | "
        f"assigned to {ryan.username} (user id {ryan.id})",
    )
    log(
        t_assign + timedelta(minutes=32),
        AuditAction.ASSET_ASSIGNED,
        f"{by_serial['LOG-MXK-BKEY-00221'].serial_number}: {by_serial['LOG-MXK-BKEY-00221'].name} | "
        f"assigned to {emily.username} (user id {emily.id})",
    )

    log(
        base + timedelta(days=8),
        AuditAction.ASSET_ASSIGNED,
        f"{by_serial['JBR-EV275-QP93L2'].serial_number}: {by_serial['JBR-EV275-QP93L2'].name} | "
        f"assigned to {olivia.username} (user id {olivia.id})",
    )
    log(
        base + timedelta(days=30),
        AuditAction.ASSET_RETURNED,
        f"{by_serial['JBR-EV275-QP93L2'].serial_number}: {by_serial['JBR-EV275-QP93L2'].name} | "
        f"returned by {olivia.username} (user id {olivia.id})",
    )

    log(
        base + timedelta(days=42),
        AuditAction.LOGIN_SUCCESS,
        f"{LOCALDEV_USERNAME} | verification login after data load",
    )

    db.session.add_all(logs)
    db.session.commit()
