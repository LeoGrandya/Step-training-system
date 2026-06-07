"""Meta endpoints: health and module ownership."""

from __future__ import annotations

from flask import Blueprint

from backend.api_utils import json_ok
from backend.module_registry import modules_as_dicts


def register(bp: Blueprint) -> None:
    @bp.get("/meta/health")
    def health():
        return json_ok(service="pose3d-web1", apiVersion="v1")

    @bp.get("/meta/modules")
    def modules():
        return json_ok(modules=modules_as_dicts())
