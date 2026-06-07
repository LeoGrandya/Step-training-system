"""Route identity helpers for short active-only MySQL unique keys."""

from __future__ import annotations

import hashlib
from typing import Any


ROUTE_IDENTITY_SEPARATOR = "\x1f"


def route_active_name_sequence_hash(name_norm: str, sequence_canon: str) -> str:
    identity = f"{name_norm}{ROUTE_IDENTITY_SEPARATOR}{sequence_canon}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def apply_active_route_identity(route: Any, *, name_norm: str, sequence_canon: str) -> None:
    route.active_name_sequence_hash = route_active_name_sequence_hash(name_norm, sequence_canon)


def clear_active_route_identity(route: Any) -> None:
    route.active_name_sequence_hash = None
