"""Shared helpers for pagination."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import Request
from sqlalchemy import func, select
from sqlalchemy.sql.selectable import Select

from app.extensions import db

DEFAULT_LIST_PER_PAGE = 20


def page_from_request(req: Request, *, arg: str = "page", default: int = 1) -> int:
    """Parse a positive page number from query args."""
    raw = req.args.get(arg, type=int)
    if raw is None:
        return default
    return max(1, raw)


@dataclass(frozen=True)
class Pagination:
    items: list[Any]
    page: int
    per_page: int
    total: int

    @property
    def pages(self) -> int:
        if self.per_page <= 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def prev_num(self) -> int | None:
        return self.page - 1 if self.has_prev else None

    @property
    def next_num(self) -> int | None:
        return self.page + 1 if self.has_next else None


def paginate_select(stmt: Select[Any], *, page: int, per_page: int) -> Pagination:
    page = max(1, page)
    total = db.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.session.scalars(stmt.offset((page - 1) * per_page).limit(per_page)))
    return Pagination(items=items, page=page, per_page=per_page, total=total)
