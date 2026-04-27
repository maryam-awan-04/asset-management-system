"""Helpers for building safe SQL ILIKE fragments for search queries."""

from __future__ import annotations


def ilike_fragment_from_query(q_raw: str | None, *, max_len: int = 80) -> str | None:
    """Return a substring safe to embed in a LIKE pattern."""
    q = (q_raw or "").strip()
    if len(q) < 1:
        return None
    q = q[:max_len].replace("%", "").replace("_", "")
    return q if q else None
