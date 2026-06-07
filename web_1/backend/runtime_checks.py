"""Runtime validation helpers for MySQL baseline."""

from __future__ import annotations

from sqlalchemy import inspect

from .db import db
from .module_registry import TABLE_OWNERS


REQUIRED_TABLES = frozenset(TABLE_OWNERS.keys()) | frozenset({"account_roles", "role_permissions", "route_steps", "analysis_results"})


def validate_mysql_schema() -> None:
    """Raise RuntimeError if required business tables are missing."""
    inspector = inspect(db.engine)
    present = set(inspector.get_table_names())
    missing = sorted(REQUIRED_TABLES - present)
    if missing:
        raise RuntimeError(
            "MySQL schema incomplete (missing tables: "
            + ", ".join(missing)
            + "). Run: cd web_1 && alembic upgrade head"
        )
