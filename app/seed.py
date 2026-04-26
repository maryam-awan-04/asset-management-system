"""Development-only data seeding."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.enums import AssetType, AuditAction, Department, RequestStatus, Role, Status
from app.extensions import db
from app.models import Asset, AssetRequest, Assignment, AuditLog, User
from app.passwords import hash_password

LOCALDEV_USERNAME = "localdev"
LOCALDEV_EMAIL = "localdev@gmail.com"

SEED_SERIAL_MARKER = "IT-LP-24-00891"
SEED_USER_PASSWORD = os.environ.get("SEED_USER_PASSWORD", "SeedDemo1!")

SEED_EMAIL_DOMAIN = "demo.com"

_DEMO_ASSET_SERIALS = frozenset(
    {
        "IT-LP-24-00891",
        "LEN-PF4ZK9Q2",
        "DELL-U3223QE-4KQ2N1",
        "DELL-P2723DE-8MZ3K9",
        "LOG-MXK-BKEY-00221",
        "APL-FVFK71Q9Q05D",
        "MSFT-SL5-9K2M4410",
        "DELL-U2424H-3N8KQ7",
        "LOG-MXM3S-11K882",
        "LOG-MXA3S-44B901",
        "JBR-EV275-QP93L2",
        "POL-P15-UK90M1",
        "ELG-FCPRO-7HX22",
        "SHR-MV7-USB-44102",
        "MSFT-M365-E5-SN8841201",
        "ADOBE-CC-TM-2025-77102",
        "DELL-P2422H-EOL-1993",
        "KEY-Q6PRO-BK88",
    },
)


def _demo_catalog_requests_already_seeded() -> bool:
    """True if the bundled request rows were already inserted (avoid duplicates on restart)."""
    sarah = db.session.scalar(
        select(User).where(User.email == f"sarah.mitchell@{SEED_EMAIL_DOMAIN}"),
    )
    laptop = db.session.scalar(
        select(Asset).where(Asset.serial_number == SEED_SERIAL_MARKER),
    )
    if sarah is None or laptop is None:
        return False
    existing = db.session.scalar(
        select(AssetRequest.id)
        .where(
            AssetRequest.user_id == sarah.id,
            AssetRequest.asset_id == laptop.id,
            AssetRequest.status == RequestStatus.APPROVED,
        )
        .limit(1),
    )
    return existing is not None


def _seed_overdue_and_requests(*, admin: User, today: date) -> None:
    """Refresh overdue dates on known catalog rows; insert bundled requests once."""
    users = db.session.scalars(
        select(User).where(User.email.like(f"%@{SEED_EMAIL_DOMAIN}")),
    ).all()
    assets = db.session.scalars(
        select(Asset).where(Asset.serial_number.in_(_DEMO_ASSET_SERIALS)),
    ).all()
    if not users or not assets:
        return

    by_username = {u.username: u for u in users}
    by_serial = {a.serial_number: a for a in assets}

    overdue_targets = {
        "IT-LP-24-00891": today - timedelta(days=9),
        "DELL-U3223QE-4KQ2N1": today - timedelta(days=5),
    }
    for serial, due_on in overdue_targets.items():
        asset = by_serial.get(serial)
        if asset is None:
            continue
        open_assignment = db.session.scalar(
            select(Assignment)
            .where(
                Assignment.asset_id == asset.id,
                Assignment.returned_date.is_(None),
            )
            .order_by(Assignment.assigned_date.desc(), Assignment.id.desc())
            .limit(1),
        )
        if open_assignment is not None:
            open_assignment.return_due_date = due_on

    if _demo_catalog_requests_already_seeded():
        return

    req_specs: list[dict] = [
        {
            "username": "priya.sharma",
            "asset_type": AssetType.MONITOR,
            "status": RequestStatus.PENDING,
            "requested_days_ago": 2,
            "note": 'Need a second 27" display for contract review workspace.',
        },
        {
            "username": "marcus.weber",
            "asset_type": AssetType.WEBCAM,
            "status": RequestStatus.PENDING,
            "requested_days_ago": 1,
            "note": "Remote onboarding interviews — dedicated webcam for interview room B.",
        },
        {
            "username": "amelia.jones",
            "asset_type": AssetType.MOUSE,
            "status": RequestStatus.PENDING,
            "requested_days_ago": 3,
            "note": "Ergonomic vertical mouse for RSI accommodation (finance).",
        },
        {
            "username": "liam.oconnor",
            "asset_type": AssetType.LICENSE,
            "status": RequestStatus.PENDING,
            "requested_days_ago": 4,
            "note": "Temporary Adobe CC seat for external counsel redlines (4 weeks).",
        },
        {
            "username": "sarah.mitchell",
            "asset_type": AssetType.LAPTOP,
            "status": RequestStatus.APPROVED,
            "requested_days_ago": 22,
            "decision_days_ago": 21,
            "asset_serial": "IT-LP-24-00891",
            "note": "Standard finance analyst laptop — issued from corporate pool.",
        },
        {
            "username": "david.nguyen",
            "asset_type": AssetType.MONITOR,
            "status": RequestStatus.APPROVED,
            "requested_days_ago": 18,
            "decision_days_ago": 17,
            "asset_serial": "DELL-U3223QE-4KQ2N1",
            "note": "Trading floor UHD monitor — approved and assigned to desk T-14.",
        },
        {
            "username": "emily.carter",
            "asset_type": AssetType.KEYBOARD,
            "status": RequestStatus.APPROVED,
            "requested_days_ago": 16,
            "decision_days_ago": 15,
            "asset_serial": "LOG-MXK-BKEY-00221",
            "note": "Engineering hot-desk keyboard — approved and deployed.",
        },
        {
            "username": "keiko.tanaka",
            "asset_type": AssetType.LAPTOP,
            "status": RequestStatus.REJECTED,
            "requested_days_ago": 12,
            "decision_days_ago": 11,
            "note": "Second laptop request declined — existing device still within refresh policy.",
        },
        {
            "username": "danielle.price",
            "asset_type": AssetType.HEADPHONES,
            "status": RequestStatus.REJECTED,
            "requested_days_ago": 8,
            "decision_days_ago": 7,
            "note": "Duplicate headset request — spare stock already allocated to team.",
        },
        {
            "username": "ryan.cooper",
            "asset_type": AssetType.MICROPHONE,
            "status": RequestStatus.REJECTED,
            "requested_days_ago": 6,
            "decision_days_ago": 5,
            "note": "Podcast kit on hold — budget frozen until Q3 planning.",
        },
    ]

    seeded_requests: list[AssetRequest] = []
    for spec in req_specs:
        requester = by_username.get(spec["username"])
        if requester is None:
            continue
        decision_date = (
            today - timedelta(days=spec["decision_days_ago"])
            if "decision_days_ago" in spec
            else None
        )
        asset_id = None
        if "asset_serial" in spec:
            selected = by_serial.get(spec["asset_serial"])
            asset_id = selected.id if selected else None
        seeded_requests.append(
            AssetRequest(
                user_id=requester.id,
                asset_type=spec["asset_type"],
                asset_id=asset_id,
                status=spec["status"],
                request_date=today - timedelta(days=spec["requested_days_ago"]),
                decision_date=decision_date,
                approved_by=(
                    admin.id if spec["status"] != RequestStatus.PENDING else None
                ),
                note=f"{spec['note']}",
            ),
        )
    if seeded_requests:
        db.session.add_all(seeded_requests)


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
            _seed_overdue_and_requests(admin=admin_existing, today=date.today())
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
            notes="Corporate finance pool — primary analyst build.",
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
            notes="STS trading floor — desk cluster T-14.",
        ),
        Asset(
            name='Dell Pro 27" P2723DE',
            asset_type=AssetType.MONITOR,
            serial_number="DELL-P2723DE-8MZ3K9",
            status=Status.ASSIGNED,
            purchase_date=date(2024, 1, 18),
            expiry_date=None,
            notes="STS operations — second screen for shift lead.",
        ),
        Asset(
            name="Logitech MX Keys S (Graphite)",
            asset_type=AssetType.KEYBOARD,
            serial_number="LOG-MXK-BKEY-00221",
            status=Status.ASSIGNED,
            purchase_date=date(2024, 5, 9),
            expiry_date=None,
            notes="Technology hot-dock — paired with TB4 dock 7.",
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
            notes="Spare pool — Legal / exec loaner.",
        ),
        Asset(
            name='Dell UltraSharp U2424H (24")',
            asset_type=AssetType.MONITOR,
            serial_number="DELL-U2424H-3N8KQ7",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 4, 22),
            expiry_date=None,
            notes="Unboxed spare — Customer & Products marketing.",
        ),
        Asset(
            name="Logitech MX Master 3S (Pale Grey)",
            asset_type=AssetType.MOUSE,
            serial_number="LOG-MXM3S-11K882",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 3, 14),
            expiry_date=None,
            notes="Spares cupboard — Technology.",
        ),
        Asset(
            name="Logitech MX Anywhere 3S",
            asset_type=AssetType.MOUSE,
            serial_number="LOG-MXA3S-44B901",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 7, 30),
            expiry_date=None,
            notes="Travel kit stock — Finance.",
        ),
        Asset(
            name="Jabra Evolve2 75 UC (Stereo)",
            asset_type=AssetType.HEADPHONES,
            serial_number="JBR-EV275-QP93L2",
            status=Status.AVAILABLE,
            purchase_date=date(2023, 10, 2),
            expiry_date=None,
            notes="Returned from contractor — inspected, ready to reissue.",
        ),
        Asset(
            name="Poly Studio P15 (Personal video bar)",
            asset_type=AssetType.WEBCAM,
            serial_number="POL-P15-UK90M1",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 2, 27),
            expiry_date=None,
            notes="Legal videoconference kit — unassigned.",
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
            notes="USB-C intermittent — with vendor RMA.",
        ),
        Asset(
            name="Microsoft 365 E5 (per-user subscription)",
            asset_type=AssetType.LICENSE,
            serial_number="MSFT-M365-E5-SN8841201",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 1, 1),
            expiry_date=date(today.year + 1, 12, 31),
            notes="Unassigned seat — provision during onboarding.",
        ),
        Asset(
            name="Adobe Creative Cloud (named user, annual)",
            asset_type=AssetType.LICENSE,
            serial_number="ADOBE-CC-TM-2025-77102",
            status=Status.AVAILABLE,
            purchase_date=date(2025, 1, 15),
            expiry_date=date(today.year, 12, 31),
            notes="Marketing shared licence — not yet assigned.",
        ),
        Asset(
            name='Dell Pro 24" P2422H (EOL)',
            asset_type=AssetType.MONITOR,
            serial_number="DELL-P2422H-EOL-1993",
            status=Status.RETIRED,
            purchase_date=date(2018, 5, 4),
            expiry_date=None,
            notes="Retired — kept for parts only.",
        ),
        Asset(
            name="Keychron Q6 Pro (100%, tactile)",
            asset_type=AssetType.KEYBOARD,
            serial_number="KEY-Q6PRO-BK88",
            status=Status.AVAILABLE,
            purchase_date=date(2024, 10, 8),
            expiry_date=None,
            notes="HR ergonomics trial — surplus after pilot.",
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

    _seed_overdue_and_requests(admin=admin, today=today)

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
