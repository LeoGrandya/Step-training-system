"""Alembic column helpers compatible with MySQL 5.5+."""

from __future__ import annotations

import sqlalchemy as sa


def json_column() -> sa.Text:
    """JSON payload stored as TEXT (MySQL 5.5 has no native JSON type)."""
    return sa.Text()
