"""Bcrypt password hashing and verification."""

from __future__ import annotations

import bcrypt

_REJECT_HASH_BYTES = bcrypt.hashpw(b"\0", bcrypt.gensalt(rounds=12))


def hash_password(plain_password: str) -> str:
    """Return ASCII bcrypt hash string."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("ascii")


def passwords_match(stored_hash: str | None, plain_password: str) -> bool:
    """Return True if the password matches the stored hash."""
    if not stored_hash:
        bcrypt.checkpw(plain_password.encode("utf-8"), _REJECT_HASH_BYTES)
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            stored_hash.encode("ascii"),
        )
    except ValueError:
        return False
