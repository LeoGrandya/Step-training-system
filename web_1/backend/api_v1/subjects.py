"""Subjects API."""

from __future__ import annotations

from flask import Blueprint, request

from backend import repositories as repo
from backend.api_utils import json_err, json_ok, list_response, parse_pagination


def _json_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None
    return payload


def _normalize_name(value):
    return " ".join(str(value or "").strip().split())


def register(bp: Blueprint) -> None:
    @bp.get("/subjects")
    def list_subjects():
        page = parse_pagination(request.args, default_limit=30)
        items, total = repo.list_subjects_page(
            keyword=page.keyword,
            is_active=page.is_active,
            limit=page.limit,
            offset=page.offset,
        )
        return list_response(items, total=total, limit=page.limit, offset=page.offset)

    @bp.post("/subjects")
    def create_subject():
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.create_subject(payload, normalize_name=_normalize_name)
        except ValueError as exc:
            return json_err(str(exc), 400)
        return json_ok(item=item)

    @bp.get("/subjects/<subject_id>")
    def get_subject(subject_id: str):
        item = repo.get_subject_payload(subject_id)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.put("/subjects/<subject_id>")
    def update_subject(subject_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            updated = repo.update_subject(subject_id, payload, normalize_name=_normalize_name)
        except ValueError as exc:
            return json_err(str(exc), 400)
        if not updated:
            return json_err("not_found", 404)
        item = repo.get_subject_payload(subject_id)
        return json_ok(item=item)

    @bp.delete("/subjects/<subject_id>")
    def delete_subject(subject_id: str):
        if not repo.soft_delete_subject(subject_id):
            return json_err("not_found", 404)
        return json_ok()
