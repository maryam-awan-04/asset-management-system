"""Seed overdue assignments and requests."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.enums import AssetType, RequestStatus
from app.extensions import db
from app.models import Asset, AssetRequest, Assignment, User
from app.seed.constants import (
    _DEMO_ASSET_SERIALS,
    SEED_EMAIL_DOMAIN,
    SEED_SERIAL_MARKER,
)


def demo_catalog_requests_already_seeded() -> bool:
    """True if the requests were already inserted."""
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


def seed_overdue_and_requests(*, admin: User, today: date) -> None:
    """Seed overdue assignments and requests."""
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

    if demo_catalog_requests_already_seeded():
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
