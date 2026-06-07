"""Seed baseline footwork_types dictionary.

Revision ID: 0002_seed_footwork_types
Revises: 0001_initial_mysql_schema
Create Date: 2026-06-03
"""

from __future__ import annotations

from datetime import datetime, timezone

from alembic import context, op
import sqlalchemy as sa


revision = "0002_seed_footwork_types"
down_revision = "0001_initial_mysql_schema"
branch_labels = None
depends_on = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


FOOTWORK_TYPES = sa.table(
    "footwork_types",
    sa.column("id", sa.String(32)),
    sa.column("code", sa.String(64)),
    sa.column("name", sa.String(120)),
    sa.column("category", sa.String(64)),
    sa.column("description", sa.Text),
    sa.column("default_start_cell", sa.Integer),
    sa.column("default_sequence", sa.String(255)),
    sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
    sa.column("deleted_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    if not context.is_offline_mode():
        bind = op.get_bind()
        existing = bind.execute(sa.text("SELECT COUNT(*) AS c FROM footwork_types")).scalar()
        if existing and int(existing) > 0:
            return

    now = _now()
    rows = [
        {
            "id": "fw_side_step",
            "code": "side_step",
            "name": "跨步",
            "category": "basic",
            "description": "横向跨步移动",
            "default_start_cell": 5,
            "default_sequence": "5",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        },
        {
            "id": "fw_parallel_step",
            "code": "parallel_step",
            "name": "并步",
            "category": "basic",
            "description": "双脚并拢移动",
            "default_start_cell": 5,
            "default_sequence": "5",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        },
        {
            "id": "fw_retreat_step",
            "code": "retreat_step",
            "name": "撤步",
            "category": "basic",
            "description": "向后撤步",
            "default_start_cell": 5,
            "default_sequence": "5",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        },
        {
            "id": "fw_two_point",
            "code": "two_point",
            "name": "两点",
            "category": "pattern",
            "description": "两点跑动",
            "default_start_cell": 5,
            "default_sequence": "5-7",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        },
        {
            "id": "fw_three_point",
            "code": "three_point",
            "name": "三点",
            "category": "pattern",
            "description": "三点跑动",
            "default_start_cell": 5,
            "default_sequence": "5-7-9",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        },
        {
            "id": "fw_four_point",
            "code": "four_point",
            "name": "四点",
            "category": "pattern",
            "description": "四点跑动",
            "default_start_cell": 5,
            "default_sequence": "5-7-9-7",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        },
    ]
    op.bulk_insert(FOOTWORK_TYPES, rows)


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM footwork_types WHERE id IN ("
            "'fw_side_step','fw_parallel_step','fw_retreat_step',"
            "'fw_two_point','fw_three_point','fw_four_point'"
            ")"
        )
    )
