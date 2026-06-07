"""Authentication endpoints: register, login, password change."""

from __future__ import annotations

import hashlib
import secrets

from flask import Blueprint, request

from backend import repositories as repo
from backend.api_utils import json_err, json_ok
from backend.models import Account, AccountRole, Role


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2:sha256:100000${salt}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, rest = stored.split("$", 1)
        if algo != "pbkdf2:sha256:100000":
            return stored == _hash_password(password)
        salt, dk_hex = rest.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def _json_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None
    return payload


def _serialize_account_with_roles(row: Account) -> dict:
    roles = (
        Role.query.join(AccountRole, AccountRole.role_id == Role.id)
        .filter(AccountRole.account_id == row.id)
        .with_entities(Role.code, Role.name)
        .all()
    )
    return {
        "id": row.id,
        "account": row.account,
        "username": row.username,
        "status": row.status,
        "roles": [{"code": r.code, "name": r.name} for r in roles],
        "createdAt": row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None,
        "updatedAt": row.updated_at.isoformat().replace("+00:00", "Z") if row.updated_at else None,
    }


def register(bp: Blueprint) -> None:
    @bp.post("/auth/register")
    def register_account():
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)

        account = str(payload.get("account") or "").strip()
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "").strip()

        if not account:
            return json_err("account_required", 400)
        if not username:
            return json_err("username_required", 400)
        if len(password) < 4:
            return json_err("password_too_short", 400)

        if Account.query.filter(Account.account == account).first() is not None:
            return json_err("duplicate_account", 409)

        try:
            row = repo.create_account_record({
                "account": account,
                "username": username,
                "passwordHash": _hash_password(password),
            })
        except repo.DuplicateRecordError:
            return json_err("duplicate_account", 409)

        return json_ok(item=_serialize_account_with_roles(Account.query.get(row["id"])))

    @bp.post("/auth/login")
    def login():
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)

        account = str(payload.get("account") or "").strip()
        password = str(payload.get("password") or "").strip()

        if not account or not password:
            return json_err("account_and_password_required", 400)

        row = Account.query.filter(Account.account == account, Account.status == "active").first()
        if row is None or not _verify_password(password, row.password_hash):
            return json_err("invalid_credentials", 401)

        return json_ok(item=_serialize_account_with_roles(row))

    @bp.get("/auth/me")
    def get_me():
        account_id = (request.headers.get("X-Account-Id") or "").strip()
        if not account_id:
            return json_err("not_authenticated", 401)
        row = Account.query.filter(Account.id == account_id, Account.status == "active").first()
        if row is None:
            return json_err("not_found", 404)
        return json_ok(item=_serialize_account_with_roles(row))

    @bp.put("/auth/password")
    def change_password():
        account_id = (request.headers.get("X-Account-Id") or "").strip()
        if not account_id:
            return json_err("not_authenticated", 401)

        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)

        old_password = str(payload.get("oldPassword") or "").strip()
        new_password = str(payload.get("newPassword") or "").strip()

        row = Account.query.filter(Account.id == account_id, Account.status == "active").first()
        if row is None:
            return json_err("not_found", 404)

        if not _verify_password(old_password, row.password_hash):
            return json_err("invalid_old_password", 400)
        if len(new_password) < 4:
            return json_err("password_too_short", 400)

        row.password_hash = _hash_password(new_password)
        row.updated_at = repo.now_utc()
        repo.db.session.commit()
        return json_ok()
