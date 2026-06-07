"""Route definitions and route steps API."""

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
    @bp.get("/routes")
    def list_routes():
        page = parse_pagination(request.args, default_limit=30)
        footwork_type_id = (request.args.get("footworkTypeId") or request.args.get("footwork_type_id") or "").strip()
        items, total = repo.list_routes_page(
            keyword=page.keyword,
            footwork_type_id=footwork_type_id or None,
            limit=page.limit,
            offset=page.offset,
        )
        return list_response(items, total=total, limit=page.limit, offset=page.offset)

    @bp.post("/routes")
    def create_route():
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.create_route_record(payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.InvalidReferenceError:
            return json_err("invalid_reference", 409)
        except repo.DuplicateRecordError as exc:
            return _conflict_error(exc)
        return json_ok(item=item)

    @bp.get("/routes/<route_id>")
    def get_route(route_id: str):
        item = repo.get_route_payload(route_id)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.put("/routes/<route_id>")
    def update_route(route_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.update_route_record(route_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.InvalidReferenceError:
            return json_err("invalid_reference", 409)
        except repo.DuplicateRecordError as exc:
            return _conflict_error(exc)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.delete("/routes/<route_id>")
    def delete_route(route_id: str):
        if not repo.soft_delete_route_record(route_id):
            return json_err("not_found", 404)
        return json_ok()

    @bp.get("/routes/<route_id>/steps")
    def list_route_steps(route_id: str):
        page = parse_pagination(request.args, default_limit=50)
        result = repo.list_route_steps_page(route_id, limit=page.limit, offset=page.offset)
        if result is None:
            return json_err("not_found", 404)
        items, total = result
        return list_response(items, total=total, limit=page.limit, offset=page.offset)

    @bp.post("/routes/<route_id>/steps")
    def create_route_step(route_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.create_route_step_record(route_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.DuplicateRecordError as exc:
            return _conflict_error(exc)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.put("/routes/<route_id>/steps/<step_id>")
    def update_route_step(route_id: str, step_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.update_route_step_record(route_id, step_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.DuplicateRecordError as exc:
            return _conflict_error(exc)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.delete("/routes/<route_id>/steps/<step_id>")
    def delete_route_step(route_id: str, step_id: str):
        if not repo.delete_route_step_record(route_id, step_id):
            return json_err("not_found", 404)
        return json_ok()
