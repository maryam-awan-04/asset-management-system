"""SQLAlchemy models for the asset-management schema."""

from __future__ import annotations

from datetime import date, datetime, timezone

from flask_login import UserMixin
from sqlalchemy import Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import AssetType, AuditAction, Department, Role, Status
from app.extensions import db


def _utc_now() -> datetime:
    """UTC timestamp for AuditLog table."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """Application user and login identity."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(db.String(256), nullable=False)
    role: Mapped[Role] = mapped_column(db.Enum(Role), nullable=False, default=Role.USER)
    department: Mapped[Department] = mapped_column(db.Enum(Department), nullable=False)

    # One user can map to many assignments (delete assignments when user is deleted, keep audit logs)
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")

    __table_args__ = (Index("ix_users_username", "username"),)

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"


class Asset(db.Model):
    """Hardware/software asset (laptop, monitor, license, etc.)."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(200), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(db.Enum(AssetType), nullable=False)
    serial_number: Mapped[str] = mapped_column(
        db.String(128), unique=True, nullable=False
    )
    status: Mapped[Status] = mapped_column(db.Enum(Status), nullable=False)
    purchase_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset {self.name!r}>"


class Assignment(db.Model):
    """Links one asset to one user for a period of time."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        db.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assigned_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    return_due_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)
    returned_date: Mapped[date | None] = mapped_column(db.Date, nullable=True)

    # Each Assignment row points to one asset and one user.
    asset: Mapped["Asset"] = relationship(back_populates="assignments")
    user: Mapped["User"] = relationship(back_populates="assignments")

    def __repr__(self) -> str:
        return f"<Assignment asset={self.asset_id} user={self.user_id}>"


class AuditLog(db.Model):
    """Audit logs for security and accountability."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[AuditAction] = mapped_column(db.Enum(AuditAction), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), nullable=False, default=_utc_now
    )
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")

    __table_args__ = (Index("ix_audit_logs_timestamp", "timestamp"),)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action!r}>"
