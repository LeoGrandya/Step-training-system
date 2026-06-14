"""Shared API helpers: pagination, JSON envelopes, password hashing for /api/v1 and legacy routes."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Any

from flask import jsonify, request


DEFAULT_LIMIT = 30
MAX_LIMIT = 200


def hash_password(password: str) -> str:
    """PBKDF2-SHA256 with per-password random salt."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2:sha256:100000${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a hash produced by hash_password()."""
    try:
        algo, rest = stored.split("$", 1)
        if algo != "pbkdf2:sha256:100000":
            return False
        salt, dk_hex = rest.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except ValueError:
        return False


def get_account_id_from_headers() -> str | None:
    """Extract X-Account-Id from request headers (shared helper)."""
    return (request.headers.get("X-Account-Id") or "").strip() or None


@dataclass(frozen=True)
class PaginationParams:
    limit: int | None
    offset: int
    keyword: str | None
    is_active: bool | None


def parse_bool_query(raw: str | None) -> bool | None:
    if raw is None or raw == "":
        return None
    value = raw.strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    return None


def parse_pagination(args, *, default_limit: int | None = DEFAULT_LIMIT) -> PaginationParams:
    """Parse list query params from Flask request.args mapping."""
    keyword = (args.get("keyword") or "").strip() or None
    is_active = parse_bool_query(args.get("is_active"))

    limit_raw = args.get("limit")
    if limit_raw is None or str(limit_raw).strip() == "":
        limit: int | None = default_limit
    else:
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            limit = default_limit
        if limit is not None:
            limit = max(1, min(limit, MAX_LIMIT))

    offset_raw = args.get("offset", "0")
    try:
        offset = int(offset_raw)
    except (TypeError, ValueError):
        offset = 0
    offset = max(0, offset)

    return PaginationParams(limit=limit, offset=offset, keyword=keyword, is_active=is_active)


def paginate_query(query, *, limit: int | None, offset: int):
    """Return (rows, total) for a SQLAlchemy query."""
    total = query.count()
    if limit is None:
        rows = query.all()
        return rows, total
    rows = query.limit(limit).offset(offset).all()
    return rows, total


def ok_payload(**fields: Any) -> dict[str, Any]:
    return {"ok": True, **fields}


def err_payload(error: str, **fields: Any) -> dict[str, Any]:
    return {"ok": False, "error": error, **fields}


def json_ok(status: int = 200, **fields: Any):
    return jsonify(ok_payload(**fields)), status


# 英文错误码 → 中文消息映射（仓库层抛出的 ValueError 已为中文，此处处理 API 层直接 json_err 的英文码）
_ERROR_CN: dict[str, str] = {
    "invalid_json": "无效的 JSON 格式",
    "not_found": "记录不存在",
    "permission_denied": "无操作权限",
    "invalid_reference": "关联数据不存在",
    "in_use": "被其他记录引用，无法删除",
    "subject_not_found": "受试者不存在",
    "account_required": "请填写账号",
    "username_required": "请填写用户名",
    "password_too_short": "密码长度不足",
    "duplicate_account": "账号已存在",
    "account_and_password_required": "请填写账号和密码",
    "invalid_credentials": "账号或密码错误",
    "not_authenticated": "请先登录",
    "invalid_old_password": "旧密码错误",
    "rbac_not_configured": "RBAC 未配置",
    "invalid_name_format": "姓名格式无效（需 1-50 个字符，可含中英文、数字、空格及 ._-'）",
    "invalid_camera": "无效的相机参数（仅支持 left/right）",
    "video_file_missing": "视频文件不存在或已被清理",
}


def json_err(error: str, status: int = 400, **fields: Any):
    return jsonify(err_payload(_ERROR_CN.get(error, error), **fields)), status


def list_response(
    items: list[Any],
    *,
    total: int,
    limit: int | None,
    offset: int,
    extra: dict[str, Any] | None = None,
):
    """Standard list envelope; legacy callers may ignore total/limit/offset."""
    body: dict[str, Any] = {
        "ok": True,
        "items": items,
        "total": total,
        "offset": offset,
    }
    if limit is not None:
        body["limit"] = limit
    if extra:
        body.update(extra)
    return jsonify(body)


def legacy_list_response(items: list[Any], *, paginate: PaginationParams, total: int):
    """Backward compatible: omit pagination fields when client did not pass limit."""
    if paginate.limit is None and paginate.offset == 0 and not paginate.keyword and paginate.is_active is None:
        return jsonify({"ok": True, "items": items})
    return list_response(items, total=total, limit=paginate.limit, offset=paginate.offset)
