"""Footwork types API."""

from __future__ import annotations

from flask import Blueprint, request

from backend import repositories as repo
from backend.api_utils import json_err, json_ok, list_response, parse_pagination


def _json_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None
    return payload


def _conflict_error(exc: RuntimeError):
    message = str(exc) or "conflict"
    return json_err(message, 409)


def register(bp: Blueprint) -> None:
    @bp.get("/footwork-types")
    def list_footwork_types():
        page = parse_pagination(request.args, default_limit=50)
        category = (request.args.get("category") or "").strip() or None
        sort_by = (request.args.get("sortBy") or "").strip() or None
        sort_order = (request.args.get("sortOrder") or "asc").strip()
        items, total = repo.list_footwork_types_page(
            keyword=page.keyword,
            is_active=page.is_active,
            category=category,
            limit=page.limit,
            offset=page.offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        base = repo.FootworkType.query
        base = repo.active_filter(base, repo.FootworkType, is_active=page.is_active)
        base = repo.keyword_filter_footwork(base, page.keyword)
        filters_data = repo.build_filter_aggregation(
            base, repo.FootworkType, "footwork-types",
            {"category": category},
        )

        return list_response(items, total=total, limit=page.limit, offset=page.offset,
                            extra={"filters": filters_data})

    @bp.post("/footwork-types")
    def create_footwork_type():
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.create_footwork_type_record(payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.DuplicateRecordError as exc:
            return _conflict_error(exc)
        return json_ok(item=item)

    @bp.get("/footwork-types/<item_id>")
    def get_footwork_type(item_id: str):
        item = repo.get_footwork_type_payload(item_id)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.put("/footwork-types/<item_id>")
    def update_footwork_type(item_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.update_footwork_type_record(item_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.DuplicateRecordError as exc:
            return _conflict_error(exc)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.delete("/footwork-types/<item_id>")
    def delete_footwork_type(item_id: str):
        if not repo.soft_delete_footwork_type(item_id):
            return json_err("not_found", 404)
        return json_ok()
