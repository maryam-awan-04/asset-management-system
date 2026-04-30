"""Shared WTForms helpers."""

from __future__ import annotations

from wtforms.validators import ValidationError

from app.enums import AssetType, Department


def department_choices() -> list[tuple[str, str]]:
    return [(d.name, d.value) for d in Department]


def format_department(key: str | None) -> Department | None:
    if key is None or key == "":
        return None
    try:
        return Department[key]
    except KeyError as exc:
        raise ValidationError("Invalid department.") from exc


def asset_type_choices() -> list[tuple[str, str]]:
    return [(t.name, t.value) for t in AssetType]


def format_asset_type(key: str | None) -> AssetType | None:
    if key is None or key == "":
        return None
    try:
        return AssetType[key]
    except KeyError as exc:
        raise ValidationError("Invalid asset type.") from exc
