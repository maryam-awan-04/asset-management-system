"""Helpers for resolving enum members."""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

E = TypeVar("E", bound=Enum)


def parse_enum_query_value(enum_cls: type[E], raw: str) -> E | None:
    """Return enum member by name."""
    key = raw.strip()
    if not key:
        return None
    try:
        return enum_cls[key.upper()]
    except KeyError:
        return None
