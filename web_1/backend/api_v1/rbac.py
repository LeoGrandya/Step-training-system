"""Minimal account, role, and permission management API."""

from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy import or_

from backend import repositories as repo
from backend.api_utils import json_err, json_ok, list_response, parse_pagination


def _json_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None
    return payload


def _duplicate_error(exc: RuntimeError):
    return json_err(str(exc) or "conflict", 409)


def register(bp: Blueprint) -> None:
    @bp.get("/accounts")
    def list_accounts():
        page = parse_pagination(request.args, default_limit=50)
        status = (request.args.get("status") or "").strip() or None
        sort_by = (request.args.get("sortBy") or "").strip() or None
        sort_order = (request.args.get("sortOrder") or "asc").strip()
        items, total = repo.list_accounts_page(
            keyword=page.keyword,
            status=status,
            limit=page.limit,
            offset=page.offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        base = repo.Account.query
        if page.keyword:
            pattern = f"%{page.keyword.strip()}%"
            base = base.filter(or_(repo.Account.account.like(pattern), repo.Account.username.like(pattern)))
        filters_data = repo.build_filter_aggregation(
            base, repo.Account, "accounts",
            {"status": status},
        )

        return list_response(items, total=total, limit=page.limit, offset=page.offset,
                            extra={"filters": filters_data})

    @bp.post("/accounts")
    def create_account():
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.create_account_record(payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.DuplicateRecordError as exc:
            return _duplicate_error(exc)
        return json_ok(item=item)

    @bp.get("/accounts/<account_id>")
    def get_account(account_id: str):
        item = repo.get_account_payload(account_id)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.put("/accounts/<account_id>")
    def update_account(account_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.update_account_record(account_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.DuplicateRecordError as exc:
            return _duplicate_error(exc)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.delete("/accounts/<account_id>")
    def delete_account(account_id: str):
        if not repo.delete_account_record(account_id):
            return json_err("not_found", 404)
        return json_ok()

    @bp.get("/accounts/<account_id>/roles")
    def get_account_roles(account_id: str):
        result = repo.list_roles_for_account(account_id)
        if result is None:
            return json_err("not_found", 404)
        items, total = result
        return list_response(items, total=total, limit=None, offset=0)

    @bp.put("/accounts/<account_id>/roles")
    def replace_account_roles(account_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            result = repo.replace_account_roles(account_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.InvalidReferenceError:
            return json_err("invalid_reference", 409)
        if result is None:
            return json_err("not_found", 404)
        items, total = result
        return list_response(items, total=total, limit=None, offset=0)

    @bp.get("/roles")
    def list_roles():
        page = parse_pagination(request.args, default_limit=50)
        sort_by = (request.args.get("sortBy") or "").strip() or None
        sort_order = (request.args.get("sortOrder") or "asc").strip()
        items, total = repo.list_roles_page(keyword=page.keyword, limit=page.limit, offset=page.offset,
                                            sort_by=sort_by, sort_order=sort_order)
        return list_response(items, total=total, limit=page.limit, offset=page.offset)

    @bp.post("/roles")
    def create_role():
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.create_role_record(payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.DuplicateRecordError as exc:
            return _duplicate_error(exc)
        return json_ok(item=item)

    @bp.get("/roles/<role_id>")
    def get_role(role_id: str):
        item = repo.get_role_payload(role_id)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.put("/roles/<role_id>")
    def update_role(role_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.update_role_record(role_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.DuplicateRecordError as exc:
            return _duplicate_error(exc)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.delete("/roles/<role_id>")
    def delete_role(role_id: str):
        try:
            deleted = repo.delete_role_record(role_id)
        except repo.ReferenceConflictError:
            return json_err("in_use", 409)
        if not deleted:
            return json_err("not_found", 404)
        return json_ok()

    @bp.get("/roles/<role_id>/permissions")
    def get_role_permissions(role_id: str):
        result = repo.list_permissions_for_role(role_id)
        if result is None:
            return json_err("not_found", 404)
        items, total = result
        return list_response(items, total=total, limit=None, offset=0)

    @bp.put("/roles/<role_id>/permissions")
    def replace_role_permissions(role_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            result = repo.replace_role_permissions(role_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.InvalidReferenceError:
            return json_err("invalid_reference", 409)
        if result is None:
            return json_err("not_found", 404)
        items, total = result
        return list_response(items, total=total, limit=None, offset=0)

    @bp.get("/permissions")
    def list_permissions():
        page = parse_pagination(request.args, default_limit=50)
        sort_by = (request.args.get("sortBy") or "").strip() or None
        sort_order = (request.args.get("sortOrder") or "asc").strip()
        items, total = repo.list_permissions_page(keyword=page.keyword, limit=page.limit, offset=page.offset,
                                                  sort_by=sort_by, sort_order=sort_order)
        return list_response(items, total=total, limit=page.limit, offset=page.offset)

    @bp.post("/permissions")
    def create_permission():
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.create_permission_record(payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.DuplicateRecordError as exc:
            return _duplicate_error(exc)
        return json_ok(item=item)

    @bp.get("/permissions/<permission_id>")
    def get_permission(permission_id: str):
        item = repo.get_permission_payload(permission_id)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.put("/permissions/<permission_id>")
    def update_permission(permission_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        try:
            item = repo.update_permission_record(permission_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.DuplicateRecordError as exc:
            return _duplicate_error(exc)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.delete("/permissions/<permission_id>")
    def delete_permission(permission_id: str):
        try:
            deleted = repo.delete_permission_record(permission_id)
        except repo.ReferenceConflictError:
            return json_err("in_use", 409)
        if not deleted:
            return json_err("not_found", 404)
        return json_ok()
