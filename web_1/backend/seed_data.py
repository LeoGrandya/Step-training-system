"""Idempotent seed payloads for baseline business dictionaries."""

from __future__ import annotations

from datetime import datetime, timezone


def _ts() -> datetime:
    return datetime.now(timezone.utc)


FOOTWORK_TYPE_SEEDS: tuple[dict[str, object], ...] = (
    {
        "id": "fw_side_step",
        "code": "side_step",
        "name": "跨步",
        "category": "basic",
        "description": "横向跨步移动",
        "default_start_cell": 5,
        "default_sequence": "5",
        "is_active": True,
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
    },
)
