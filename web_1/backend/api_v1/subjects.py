"""Subjects API — 受试者操作限定在当前登录账号的数据范围内。"""

from __future__ import annotations

from flask import Blueprint, request

from backend import repositories as repo
from backend.api_utils import json_err, json_ok, list_response, parse_pagination
from backend.models import Subject


def _json_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None
    return payload


def _normalize_name(value):
    name = " ".join(str(value or "").strip().split())
    if name and not _is_valid_name(name):
        raise ValueError("invalid_name_format")
    return name

def _is_valid_name(name):
    import re
    return bool(re.match(r'^[一-鿿㐀-䶿a-zA-Z\s]+$', name))


def _account_id() -> str | None:
    return (request.headers.get("X-Account-Id") or "").strip() or None


def _check_ownership(subject_id: str, account_id: str) -> bool:
    row = Subject.query.filter(Subject.id == subject_id, Subject.is_active.is_(True)).first()
    if row is None:
        return None
    if row.created_by_account_id and row.created_by_account_id != account_id:
        return False
    return True


def register(bp: Blueprint) -> None:
    @bp.get("/subjects")
    def list_subjects():
        page = parse_pagination(request.args, default_limit=30)
        items, total = repo.list_subjects_page(
            keyword=page.keyword,
            is_active=page.is_active,
            account_id=_account_id(),
            limit=page.limit,
            offset=page.offset,
        )
        return list_response(items, total=total, limit=page.limit, offset=page.offset)

    @bp.post("/subjects")
    def create_subject():
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        aid = _account_id()
        if aid:
            payload["createdByAccountId"] = aid
        else:
            payload["createdByAccountId"] = payload.get("createdByAccountId")
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
        aid = _account_id()
        if aid:
            ok = _check_ownership(subject_id, aid)
            if ok is None:
                return json_err("not_found", 404)
            if not ok:
                return json_err("permission_denied", 403)
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
        aid = _account_id()
        if aid:
            ok = _check_ownership(subject_id, aid)
            if ok is None:
                return json_err("not_found", 404)
            if not ok:
                return json_err("permission_denied", 403)
        if not repo.soft_delete_subject(subject_id):
            return json_err("not_found", 404)
        return json_ok()
