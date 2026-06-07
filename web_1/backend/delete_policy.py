"""Soft-delete and referential-delete policy helpers for business tables."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Query

from .db import db


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# Tables that must use is_active + deleted_at instead of physical DELETE when referenced.
SOFT_DELETE_TABLES = frozenset(
    {
        "subjects",
        "footwork_types",
        "route_definitions",
    }
)

# ORM models that block physical delete of parent rows via FK ON DELETE RESTRICT.
RESTRICT_PARENT_TABLES = frozenset(
    {
        "subjects",
        "footwork_types",
        "route_definitions",
        "training_configs",
        "training_videos",
        "analysis_jobs",
    }
)


def apply_soft_delete(row: Any) -> None:
    """Mark a row inactive; expects is_active and optional deleted_at on the model."""
    row.is_active = False
    if hasattr(row, "deleted_at"):
        row.deleted_at = now_utc()
    if hasattr(row, "updated_at"):
        row.updated_at = now_utc()


def active_filter(query: Query, model: Any, *, is_active: bool | None) -> Query:
    if is_active is None:
        return query.filter(model.is_active.is_(True))
    if is_active:
        return query.filter(model.is_active.is_(True))
    return query.filter(model.is_active.is_(False))


def keyword_filter(query: Query, model: Any, column: Any, keyword: str | None) -> Query:
    if not keyword:
        return query
    pattern = f"%{keyword.strip()}%"
    return query.filter(column.like(pattern))
