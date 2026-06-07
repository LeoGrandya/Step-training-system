"""Request-level RBAC guard for versioned write APIs."""

from __future__ import annotations

from flask import Blueprint, current_app, request

from backend.api_utils import json_err
from backend.models import Account, AccountRole, Permission, RolePermission

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

RESOURCE_WRITE_PERMISSIONS = {
    "subjects": "subjects.write",
    "footwork-types": "footwork-types.write",
    "routes": "routes.write",
    "training-configs": "training.write",
    "training-videos": "training.write",
    "training-stats": "training.write",
    "accounts": "rbac.write",
    "roles": "rbac.write",
    "permissions": "rbac.write",
    "evaluations": "evaluations.write",
}


def _resource_from_path() -> str:
    path = request.path.removeprefix("/api/v1/").strip("/")
    return path.split("/", 1)[0] if path else ""


def _account_has_permission(account_id: str, permission_code: str) -> bool:
    account = Account.query.filter(Account.id == account_id, Account.status == "active").first()
    if account is None:
        return False
    codes = (
        Permission.query.join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(AccountRole, AccountRole.role_id == RolePermission.role_id)
        .filter(AccountRole.account_id == account_id)
        .with_entities(Permission.code)
        .all()
    )
    granted = {row[0] for row in codes}
    return "admin.all" in granted or permission_code in granted


def _active_account_count() -> int:
    return Account.query.filter(Account.status == "active").count()


def _has_permission_assignments() -> bool:
    return db_has_role_permissions()


def db_has_role_permissions() -> bool:
    return RolePermission.query.first() is not None


def register_rbac_guard(bp: Blueprint) -> None:
    @bp.before_request
    def require_write_permission():
        if not current_app.config.get("API_V1_RBAC_ENABLED", False):
            return None
        if request.method not in WRITE_METHODS:
            return None

        resource = _resource_from_path()
        required = RESOURCE_WRITE_PERMISSIONS.get(resource)
        if required is None:
            return None

        if _active_account_count() == 0:
            if resource == "accounts" and request.method == "POST":
                return None
            return json_err("rbac_not_configured", 403)

        if not _has_permission_assignments() and resource in {"accounts", "roles", "permissions"}:
            return None

        account_id = (request.headers.get("X-Account-Id") or "").strip()
        if not account_id or not _account_has_permission(account_id, required):
            return json_err("permission_denied", 403)
        return None
