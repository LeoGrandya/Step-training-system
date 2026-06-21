"""Repository helpers that preserve old API shapes over the MySQL schema."""

from __future__ import annotations

import json
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from .db import db
from .api_utils import hash_password, paginate_query
from .delete_policy import active_filter, apply_soft_delete, keyword_filter
from .models import (
    Account,
    AccountRole,
    AnalysisJob,
    AnalysisResult,
    EvaluationRecord,
    FootworkType,
    KinematicsDataset,
    KinematicsFrameMetric,
    Permission,
    Report,
    RouteDefinition,
    RouteStep,
    Role,
    RolePermission,
    Subject,
    TrainingConfig,
    TrainingVideo,
    now_utc,
)
from .route_identity import (
    apply_active_route_identity,
    clear_active_route_identity,
    route_active_name_sequence_hash,
)


class DuplicateRecordError(RuntimeError):
    """Raised when a compatibility create/update hits a unique business key."""


class InvalidReferenceError(RuntimeError):
    """Raised when a request points at a missing referenced row."""


class ReferenceConflictError(RuntimeError):
    """Raised when a delete would break a known business reference."""


def now_iso_utc() -> str:
    return now_utc().isoformat().replace("+00:00", "Z")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


def _json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value if value is not None else {}


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _none_if_blank(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _int_or_none(value: Any, *, field: str, minimum: int | None = None, maximum: int | None = None) -> int | None:
    if value in (None, ""):
        return None
    try:
        out = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_{field}") from exc
    if minimum is not None and out < minimum:
        raise ValueError(f"invalid_{field}")
    if maximum is not None and out > maximum:
        raise ValueError(f"invalid_{field}")
    return out


def _float_or_none(value: Any, *, field: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_{field}") from exc


def _bool_value(value: Any, *, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _canonical_sequence(value: Any) -> str:
    text = str(value or "").strip().upper()
    for old in ("，", "、", ";", "；", "\r", "\n", " "):
        text = text.replace(old, ",")
    while ",," in text:
        text = text.replace(",,", ",")
    return text.strip(",")


def _require_active_subject(subject_id: str | None) -> str:
    if not subject_id:
        raise InvalidReferenceError("关联数据不存在")
    row = Subject.query.filter(Subject.id == subject_id, Subject.is_active.is_(True)).first()
    if row is None:
        raise InvalidReferenceError("关联数据不存在")
    return subject_id


def _require_active_footwork_type(footwork_type_id: str | None) -> str | None:
    if not footwork_type_id:
        return None
    row = FootworkType.query.filter(FootworkType.id == footwork_type_id, FootworkType.is_active.is_(True)).first()
    if row is None:
        raise InvalidReferenceError("关联数据不存在")
    return footwork_type_id


def _require_active_route(route_definition_id: str | None) -> str | None:
    if not route_definition_id:
        return None
    row = RouteDefinition.query.filter(
        RouteDefinition.id == route_definition_id,
        RouteDefinition.is_active.is_(True),
    ).first()
    if row is None:
        raise InvalidReferenceError("关联数据不存在")
    return route_definition_id


def _require_training_config(training_config_id: str | None) -> str | None:
    if not training_config_id:
        return None
    if TrainingConfig.query.filter(TrainingConfig.id == training_config_id).first() is None:
        raise InvalidReferenceError("关联数据不存在")
    return training_config_id


def _get_training_config_row(training_config_id: str | None) -> TrainingConfig | None:
    if not training_config_id:
        return None
    row = TrainingConfig.query.filter(TrainingConfig.id == training_config_id).first()
    if row is None:
        raise InvalidReferenceError("关联数据不存在")
    return row


def _require_training_video(training_video_id: str | None) -> str | None:
    if not training_video_id:
        return None
    if TrainingVideo.query.filter(TrainingVideo.id == training_video_id).first() is None:
        raise InvalidReferenceError("关联数据不存在")
    return training_video_id


def _require_analysis_job(job_id: str | None) -> str | None:
    if not job_id:
        return None
    if AnalysisJob.query.filter(AnalysisJob.job_id == job_id).first() is None:
        raise InvalidReferenceError("关联数据不存在")
    return job_id


def _get_analysis_job_row(job_id: str | None) -> AnalysisJob | None:
    if not job_id:
        return None
    row = AnalysisJob.query.filter(AnalysisJob.job_id == job_id).first()
    if row is None:
        raise InvalidReferenceError("关联数据不存在")
    return row


def _require_kinematics_dataset(dataset_id: str | None) -> str | None:
    if not dataset_id:
        return None
    if KinematicsDataset.query.filter(KinematicsDataset.id == dataset_id).first() is None:
        raise InvalidReferenceError("关联数据不存在")
    return dataset_id


def _get_kinematics_dataset_row(dataset_id: str | None) -> KinematicsDataset | None:
    if not dataset_id:
        return None
    row = KinematicsDataset.query.filter(KinematicsDataset.id == dataset_id).first()
    if row is None:
        raise InvalidReferenceError("关联数据不存在")
    return row


def init_db_runtime() -> None:
    """Compatibility hook for old routes; schema is managed by Alembic."""
    return None


def subject_exists(subject_id: str) -> bool:
    return (
        db.session.query(Subject.id)
        .filter(Subject.id == subject_id, Subject.is_active.is_(True))
        .first()
        is not None
    )


def serialize_subject(subject: Subject) -> dict[str, Any]:
    return {
        "id": subject.id,
        "name": subject.name,
        "age": subject.age,
        "heightCm": subject.height_cm,
        "weightKg": subject.weight_kg,
        "hand": subject.hand,
        "years": subject.years,
        "level": subject.level,
        "createdByAccountId": subject.created_by_account_id,
        "createdAt": _iso(subject.created_at),
        "updatedAt": _iso(subject.updated_at),
    }


def _distinguish_suffix(subject_dict: dict[str, Any]) -> str:
    """Return distinguishing suffix for duplicate names: age > height > weight. Empty if none."""
    if subject_dict.get("age") is not None:
        return f"{subject_dict['age']}岁"
    if subject_dict.get("heightCm") is not None:
        return f"{subject_dict['heightCm']}cm"
    if subject_dict.get("weightKg") is not None:
        return f"{subject_dict['weightKg']}kg"
    return ""


def _compute_display_names(subjects: list[dict[str, Any]]) -> None:
    """Mutate subjects in-place: add displayName. Later duplicates get distinguishing suffix."""
    groups: dict[tuple[str | None, str], list[dict[str, Any]]] = {}
    for s in subjects:
        key = (s.get("createdByAccountId"), s["name"])
        groups.setdefault(key, []).append(s)

    for group in groups.values():
        if len(group) <= 1:
            for s in group:
                s["displayName"] = s["name"]
            continue
        group.sort(key=lambda s: s.get("createdAt", ""))
        for i, s in enumerate(group):
            if i == 0:
                s["displayName"] = s["name"]
            else:
                suffix = _distinguish_suffix(s)
                s["displayName"] = f"{s['name']}·{suffix}" if suffix else s["name"]


def list_subjects() -> list[dict[str, Any]]:
    items, _ = list_subjects_page(limit=None, offset=0)
    return items


def list_subjects_page(
    *,
    keyword: str | None = None,
    is_active: bool | None = None,
    account_id: str | None = None,
    hand: str | None = None,
    level: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = Subject.query
    query = active_filter(query, Subject, is_active=is_active)
    if account_id:
        query = query.filter(Subject.created_by_account_id == account_id)
    if hand:
        query = query.filter(Subject.hand == hand)
    if level:
        query = query.filter(Subject.level == level)
    query = keyword_filter(query, Subject, Subject.name, keyword)
    query = query.order_by(Subject.name.asc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    items = [serialize_subject(row) for row in rows]
    _compute_display_names(items)
    return items, total

def serialize_footwork_type(row: FootworkType) -> dict[str, Any]:
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "category": row.category,
        "description": row.description,
        "defaultStartCell": row.default_start_cell,
        "defaultSequence": row.default_sequence,
        "isActive": row.is_active,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


def list_footwork_types_page(
    *,
    keyword: str | None = None,
    is_active: bool | None = None,
    category: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = FootworkType.query
    query = active_filter(query, FootworkType, is_active=is_active)
    if category:
        query = query.filter(FootworkType.category == category)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(FootworkType.name.like(pattern), FootworkType.code.like(pattern)))
    query = query.order_by(FootworkType.name.asc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_footwork_type(row) for row in rows], total


def get_footwork_type_payload(item_id: str) -> dict[str, Any] | None:
    row = FootworkType.query.filter(FootworkType.id == item_id, FootworkType.is_active.is_(True)).first()
    return serialize_footwork_type(row) if row else None


def _footwork_type_values_from_payload(
    payload: dict[str, Any],
    *,
    existing: FootworkType | None = None,
) -> dict[str, Any]:
    code = str(payload.get("code", existing.code if existing else "") or "").strip().lower()
    name = _clean_text(payload.get("name", existing.name if existing else ""))
    if not code:
        raise ValueError("请填写编码")
    if not name:
        raise ValueError("请填写名称")
    return {
        "code": code,
        "name": name,
        "category": _none_if_blank(payload.get("category", existing.category if existing else None)),
        "description": _none_if_blank(payload.get("description", existing.description if existing else None)),
        "default_start_cell": _int_or_none(
            payload.get("defaultStartCell", existing.default_start_cell if existing else None),
            field="default_start_cell",
        ),
        "default_sequence": _none_if_blank(
            payload.get("defaultSequence", existing.default_sequence if existing else None)
        ),
    }


def _ensure_footwork_type_code_available(*, item_id: str | None, code: str) -> None:
    query = FootworkType.query.filter(FootworkType.code == code)
    if item_id:
        query = query.filter(FootworkType.id != item_id)
    if query.first() is not None:
        raise DuplicateRecordError("编码已存在")


def create_footwork_type_record(payload: dict[str, Any]) -> dict[str, Any]:
    values = _footwork_type_values_from_payload(payload)
    _ensure_footwork_type_code_available(item_id=None, code=values["code"])
    row = FootworkType(id=_new_id("fw"), **values)
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("编码已存在") from exc
    return serialize_footwork_type(row)


def update_footwork_type_record(item_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    row = FootworkType.query.filter(FootworkType.id == item_id, FootworkType.is_active.is_(True)).first()
    if row is None:
        return None
    values = _footwork_type_values_from_payload(payload, existing=row)
    _ensure_footwork_type_code_available(item_id=item_id, code=values["code"])
    for key, value in values.items():
        setattr(row, key, value)
    row.updated_at = now_utc()
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("编码已存在") from exc
    return serialize_footwork_type(row)


def soft_delete_footwork_type(item_id: str) -> bool:
    row = FootworkType.query.filter(FootworkType.id == item_id, FootworkType.is_active.is_(True)).first()
    if row is None:
        return False
    apply_soft_delete(row)
    db.session.commit()
    return True


def create_subject(payload: dict[str, Any], *, normalize_name) -> dict[str, Any]:
    name = normalize_name(payload.get("name"))
    if not name:
        raise ValueError("请填写名称")
    try:
        age = int(payload.get("age")) if payload.get("age") else None
        height_cm = int(payload.get("heightCm")) if payload.get("heightCm") else None
        weight_kg = float(payload.get("weightKg")) if payload.get("weightKg") else None
        years = int(payload.get("years")) if payload.get("years") else 0
    except (TypeError, ValueError) as exc:
        raise ValueError("数据格式无效") from exc

    created_by = payload.get("createdByAccountId") or None

    # 同账号下同名即拦截，要求用户换名或补充区分信息
    existing = Subject.query.filter(
        Subject.name == name,
        Subject.is_active.is_(True),
        Subject.created_by_account_id == created_by,
    ).first()
    if existing is not None:
        raise ValueError("此账号下已存在同名受试者，请更换名称，或补充年龄、身高、体重等选填信息以区分")

    subject = Subject(
        id=_new_id("usr"),
        name=name,
        age=age,
        height_cm=height_cm,
        weight_kg=weight_kg,
        hand=str(payload.get("hand", "右手")).lower(),
        years=years,
        level=str(payload.get("level", "业余")),
        created_by_account_id=created_by,
    )
    db.session.add(subject)
    db.session.commit()
    result = serialize_subject(subject)
    # 若存在更早创建的同名受试者，为后来者追加 displayName
    earlier = Subject.query.filter(
        Subject.name == name,
        Subject.id != subject.id,
        Subject.is_active.is_(True),
        Subject.created_by_account_id == created_by,
        Subject.created_at < subject.created_at,
    ).first()
    if earlier is not None:
        suffix = _distinguish_suffix(result)
        result["displayName"] = f"{result['name']}·{suffix}" if suffix else result["name"]
    else:
        result["displayName"] = result["name"]
    return result


def get_subject_payload(subject_id: str) -> dict[str, Any] | None:
    subject = Subject.query.filter(Subject.id == subject_id, Subject.is_active.is_(True)).first()
    if subject is None:
        return None
    result = serialize_subject(subject)
    # 检测重名：若存在更早创建的同名受试者，则为后来者追加 displayName 后缀
    earlier = Subject.query.filter(
        Subject.name == subject.name,
        Subject.id != subject.id,
        Subject.is_active.is_(True),
        Subject.created_by_account_id == subject.created_by_account_id,
        Subject.created_at < subject.created_at,
    ).first()
    if earlier is not None:
        suffix = _distinguish_suffix(result)
        result["displayName"] = f"{result['name']}·{suffix}" if suffix else result["name"]
    else:
        result["displayName"] = result["name"]
    return result


def cleanup_duplicate_subjects() -> int:
    """Soft-delete later subjects that are exact attribute duplicates (same name, account, age/height/weight).
    Returns the count of deleted subjects."""
    all_subjects = Subject.query.filter(Subject.is_active.is_(True)).all()
    groups: dict[tuple[str | None, str], list[Subject]] = {}
    for s in all_subjects:
        key = (s.created_by_account_id, s.name)
        groups.setdefault(key, []).append(s)

    deleted = 0
    for group in groups.values():
        if len(group) <= 1:
            continue
        group.sort(key=lambda s: s.created_at)
        first = group[0]
        for later in group[1:]:
            if (
                later.age == first.age
                and later.height_cm == first.height_cm
                and later.weight_kg == first.weight_kg
            ):
                apply_soft_delete(later)
                deleted += 1

    if deleted:
        db.session.commit()
    return deleted


def update_subject(subject_id: str, payload: dict[str, Any], *, normalize_name) -> bool:
    subject = Subject.query.filter(Subject.id == subject_id, Subject.is_active.is_(True)).first()
    if subject is None:
        return False
    name = normalize_name(payload.get("name", subject.name))
    if not name:
        raise ValueError("请填写名称")
    try:
        if "age" in payload:
            subject.age = int(payload.get("age")) if payload.get("age") else None
        if "heightCm" in payload:
            subject.height_cm = int(payload.get("heightCm")) if payload.get("heightCm") else None
        if "weightKg" in payload:
            subject.weight_kg = float(payload.get("weightKg")) if payload.get("weightKg") else None
        if "years" in payload:
            subject.years = int(payload.get("years")) if payload.get("years") else 0
    except (TypeError, ValueError) as exc:
        raise ValueError("数据格式无效") from exc
    subject.name = name
    if "hand" in payload:
        subject.hand = str(payload.get("hand")).lower()
    if "level" in payload:
        subject.level = str(payload.get("level"))
    subject.updated_at = now_utc()
    db.session.commit()
    return True


def soft_delete_subject(subject_id: str) -> bool:
    subject = Subject.query.filter(Subject.id == subject_id, Subject.is_active.is_(True)).first()
    if subject is None:
        return False
    # 级联清理运动学数据（物理删除 datasets + 逐帧指标）
    datasets = KinematicsDataset.query.filter(KinematicsDataset.subject_id == subject_id).all()
    for ds in datasets:
        KinematicsFrameMetric.query.filter(KinematicsFrameMetric.dataset_id == ds.id).delete()
        db.session.delete(ds)
    # 清理关联的评估记录
    EvaluationRecord.query.filter(EvaluationRecord.subject_id == subject_id).delete()
    apply_soft_delete(subject)
    db.session.commit()
    return True


def check_subject_ownership(subject_id: str, account_id: str) -> bool | None:
    """Return True if owned by account, False if owned by someone else, None if not found."""
    subject = Subject.query.filter(Subject.id == subject_id, Subject.is_active.is_(True)).first()
    if subject is None:
        return None
    if subject.created_by_account_id and subject.created_by_account_id != account_id:
        return False
    return True


def _subject_ids_for_account(account_id: str) -> list[str]:
    """Return all active subject IDs belonging to an account."""
    rows = db.session.query(Subject.id).filter(
        Subject.created_by_account_id == account_id,
        Subject.is_active.is_(True),
    ).all()
    return [r[0] for r in rows]


def check_report_ownership(report_id: str, account_id: str) -> bool | None:
    """Return True if report's subject is owned by account, False otherwise, None if report not found."""
    report = Report.query.filter(Report.id == report_id).first()
    if report is None:
        return None
    return check_subject_ownership(report.subject_id, account_id)


def serialize_custom_footwork(route: RouteDefinition) -> dict[str, Any]:
    return {
        "id": route.id,
        "name": route.name,
        "sequence": route.sequence,
        "startCell": route.start_cell,
        "rhythm": _json(route.rhythm_json),
        "actionRequirements": route.action_requirements,
        "savedAt": _iso(route.created_at),
    }


def list_custom_footworks() -> list[dict[str, Any]]:
    items, _ = list_custom_footworks_page(limit=None, offset=0)
    return items


def list_custom_footworks_page(
    *,
    keyword: str | None = None,
    footwork_type_id: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = RouteDefinition.query.filter(
        RouteDefinition.is_custom.is_(True),
        RouteDefinition.is_active.is_(True),
    )
    query = keyword_filter(query, RouteDefinition, RouteDefinition.name, keyword)
    if footwork_type_id:
        query = query.filter(RouteDefinition.footwork_type_id == footwork_type_id)
    query = query.order_by(RouteDefinition.created_at.desc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_custom_footwork(row) for row in rows], total


def create_custom_footwork_record(
    *,
    name: str,
    sequence: str,
    sequence_canon: str,
    start_cell: int,
    rhythm: Any = None,
    action_requirements: str | None = None,
) -> dict[str, Any]:
    active_hash = route_active_name_sequence_hash(name, sequence_canon)
    if (
        RouteDefinition.query.filter(
            RouteDefinition.active_name_sequence_hash == active_hash,
            RouteDefinition.is_active.is_(True),
        ).first()
        is not None
    ):
        raise DuplicateRecordError("名称与序列组合已存在")
    route = RouteDefinition(
        id=_new_id("cf"),
        name=name,
        name_norm=name,
        sequence=sequence,
        sequence_canon=sequence_canon,
        active_name_sequence_hash=active_hash,
        start_cell=start_cell,
        rhythm_json=rhythm if isinstance(rhythm, (dict, list)) else None,
        action_requirements=_none_if_blank(action_requirements),
        is_custom=True,
        is_active=True,
    )
    db.session.add(route)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("名称与序列组合已存在") from exc
    return serialize_custom_footwork(route)


def update_custom_footwork_record(
    item_id: str,
    *,
    name: str,
    sequence: str,
    sequence_canon: str,
    start_cell: int,
    rhythm: Any = None,
    action_requirements: str | None = None,
) -> dict[str, Any] | None:
    route = RouteDefinition.query.filter(
        RouteDefinition.id == item_id,
        RouteDefinition.is_custom.is_(True),
        RouteDefinition.is_active.is_(True),
    ).first()
    if route is None:
        return None
    active_hash = route_active_name_sequence_hash(name, sequence_canon)
    duplicate = RouteDefinition.query.filter(
        RouteDefinition.id != item_id,
        RouteDefinition.active_name_sequence_hash == active_hash,
        RouteDefinition.is_active.is_(True),
    ).first()
    if duplicate is not None:
        raise DuplicateRecordError("名称与序列组合已存在")
    route.name = name
    route.name_norm = name
    route.sequence = sequence
    route.sequence_canon = sequence_canon
    apply_active_route_identity(route, name_norm=name, sequence_canon=sequence_canon)
    route.start_cell = start_cell
    route.rhythm_json = rhythm if isinstance(rhythm, (dict, list)) else None
    route.action_requirements = _none_if_blank(action_requirements)
    route.updated_at = now_utc()
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("名称与序列组合已存在") from exc
    return serialize_custom_footwork(route)


def soft_delete_custom_footwork(item_id: str) -> bool:
    route = RouteDefinition.query.filter(
        RouteDefinition.id == item_id,
        RouteDefinition.is_custom.is_(True),
        RouteDefinition.is_active.is_(True),
    ).first()
    if route is None:
        return False
    clear_active_route_identity(route)
    apply_soft_delete(route)
    db.session.commit()
    return True


def serialize_route(route: RouteDefinition) -> dict[str, Any]:
    rhythm = _json(route.rhythm_json)
    return {
        "id": route.id,
        "footworkTypeId": route.footwork_type_id,
        "name": route.name,
        "sequence": route.sequence,
        "sequenceCanon": route.sequence_canon,
        "startCell": route.start_cell,
        "rhythm": rhythm,
        "defaultMs": rhythm.get("defaultMs") if isinstance(rhythm, dict) else None,
        "actionRequirements": route.action_requirements,
        "isCustom": route.is_custom,
        "isActive": route.is_active,
        "createdAt": _iso(route.created_at),
        "updatedAt": _iso(route.updated_at),
        "deletedAt": _iso(route.deleted_at),
    }


def list_routes_page(
    *,
    keyword: str | None = None,
    footwork_type_id: str | None = None,
    account_id: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = RouteDefinition.query.filter(RouteDefinition.is_active.is_(True))
    if account_id:
        query = query.filter(
            (RouteDefinition.created_by_account_id == account_id)
            | (RouteDefinition.created_by_account_id.is_(None))
        )
    if footwork_type_id:
        query = query.filter(RouteDefinition.footwork_type_id == footwork_type_id)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                RouteDefinition.id.like(pattern),
                RouteDefinition.name.like(pattern),
                RouteDefinition.sequence.like(pattern),
                RouteDefinition.action_requirements.like(pattern),
            )
        )
    query = query.order_by(RouteDefinition.updated_at.desc(), RouteDefinition.created_at.desc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_route(row) for row in rows], total


def get_route_payload(route_id: str) -> dict[str, Any] | None:
    route = RouteDefinition.query.filter(RouteDefinition.id == route_id, RouteDefinition.is_active.is_(True)).first()
    return serialize_route(route) if route else None


def _route_values_from_payload(payload: dict[str, Any], *, existing: RouteDefinition | None = None) -> dict[str, Any]:
    name = _clean_text(payload.get("name", existing.name if existing else ""))
    sequence = str(payload.get("sequence", existing.sequence if existing else "") or "").strip()
    sequence_canon = _canonical_sequence(sequence)
    start_default = existing.start_cell if existing else None
    start_cell = _int_or_none(payload.get("startCell", start_default), field="start_cell", minimum=1, maximum=9)

    if not name:
        raise ValueError("请填写名称")
    if not sequence_canon:
        raise ValueError("请填写序列")
    if start_cell is None:
        raise ValueError("起始宫格无效（1-9）")

    footwork_type_id = payload.get("footworkTypeId", existing.footwork_type_id if existing else None)
    footwork_type_id = _require_active_footwork_type(_none_if_blank(footwork_type_id))
    # rhythm: 前端发 defaultMs 数字 → 后端存 rhytm_json = {"defaultMs": value}
    default_ms = payload.get("defaultMs")
    if default_ms is not None:
        rhythm_json = {"defaultMs": int(default_ms)}
    elif existing and existing.rhythm_json:
        rhythm_json = existing.rhythm_json
    else:
        rhythm_json = None
    action_requirements = payload.get(
        "actionRequirements",
        existing.action_requirements if existing else None,
    )
    return {
        "name": name,
        "name_norm": name,
        "sequence": sequence,
        "sequence_canon": sequence_canon,
        "start_cell": start_cell,
        "footwork_type_id": footwork_type_id,
        "rhythm_json": rhythm_json,
        "action_requirements": _none_if_blank(action_requirements),
        "created_by_account_id": (
            payload.get("createdByAccountId")
            or (existing.created_by_account_id if existing else None)
        ),
    }


def _ensure_route_identity_available(*, route_id: str | None, name: str, sequence_canon: str) -> str:
    active_hash = route_active_name_sequence_hash(name, sequence_canon)
    query = RouteDefinition.query.filter(
        RouteDefinition.active_name_sequence_hash == active_hash,
        RouteDefinition.is_active.is_(True),
    )
    if route_id:
        query = query.filter(RouteDefinition.id != route_id)
    if query.first() is not None:
        raise DuplicateRecordError("名称与序列组合已存在")
    return active_hash


def create_route_record(payload: dict[str, Any]) -> dict[str, Any]:
    values = _route_values_from_payload(payload)
    active_hash = _ensure_route_identity_available(
        route_id=None,
        name=values["name_norm"],
        sequence_canon=values["sequence_canon"],
    )
    route = RouteDefinition(
        id=_new_id("rte"),
        footwork_type_id=values["footwork_type_id"],
        name=values["name"],
        name_norm=values["name_norm"],
        sequence=values["sequence"],
        sequence_canon=values["sequence_canon"],
        active_name_sequence_hash=active_hash,
        start_cell=values["start_cell"],
        rhythm_json=values["rhythm_json"],
        action_requirements=values["action_requirements"],
        created_by_account_id=values.get("created_by_account_id"),
        is_custom=True,
        is_active=True,
    )
    db.session.add(route)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("名称与序列组合已存在") from exc
    return serialize_route(route)


def update_route_record(route_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    route = RouteDefinition.query.filter(RouteDefinition.id == route_id, RouteDefinition.is_active.is_(True)).first()
    if route is None:
        return None
    values = _route_values_from_payload(payload, existing=route)
    _ensure_route_identity_available(
        route_id=route_id,
        name=values["name_norm"],
        sequence_canon=values["sequence_canon"],
    )
    route.footwork_type_id = values["footwork_type_id"]
    route.name = values["name"]
    route.name_norm = values["name_norm"]
    route.sequence = values["sequence"]
    route.sequence_canon = values["sequence_canon"]
    apply_active_route_identity(route, name_norm=values["name_norm"], sequence_canon=values["sequence_canon"])
    route.start_cell = values["start_cell"]
    route.rhythm_json = values["rhythm_json"]
    route.action_requirements = values["action_requirements"]
    route.updated_at = now_utc()
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("名称与序列组合已存在") from exc
    return serialize_route(route)


def soft_delete_route_record(route_id: str) -> bool:
    route = RouteDefinition.query.filter(RouteDefinition.id == route_id, RouteDefinition.is_active.is_(True)).first()
    if route is None:
        return False
    clear_active_route_identity(route)
    apply_soft_delete(route)
    db.session.commit()
    return True


def serialize_route_step(step: RouteStep) -> dict[str, Any]:
    return {
        "id": step.id,
        "routeDefinitionId": step.route_definition_id,
        "stepOrder": step.step_order,
        "cell": step.cell,
        "actionType": step.action_type,
        "dwellMs": step.dwell_ms,
        "rhythmMs": step.rhythm_ms,
        "note": step.note,
    }


def list_route_steps_page(
    route_id: str,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int] | None:
    if get_route_payload(route_id) is None:
        return None
    query = RouteStep.query.filter(RouteStep.route_definition_id == route_id).order_by(RouteStep.step_order.asc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_route_step(row) for row in rows], total


def _route_step_values_from_payload(payload: dict[str, Any], *, existing: RouteStep | None = None) -> dict[str, Any]:
    step_order = _int_or_none(
        payload.get("stepOrder", existing.step_order if existing else None),
        field="step_order",
        minimum=0,
    )
    cell = _int_or_none(payload.get("cell", existing.cell if existing else None), field="cell", minimum=1, maximum=9)
    if step_order is None:
        raise ValueError("步骤顺序无效")
    if cell is None:
        raise ValueError("宫格编号无效（1-9）")
    dwell_ms = _int_or_none(payload.get("dwellMs", existing.dwell_ms if existing else None), field="dwell_ms", minimum=0)
    rhythm_ms = _int_or_none(
        payload.get("rhythmMs", existing.rhythm_ms if existing else None),
        field="rhythm_ms",
        minimum=0,
    )
    return {
        "step_order": step_order,
        "cell": cell,
        "action_type": _none_if_blank(payload.get("actionType", existing.action_type if existing else None)),
        "dwell_ms": dwell_ms,
        "rhythm_ms": rhythm_ms,
        "note": _none_if_blank(payload.get("note", existing.note if existing else None)),
    }


def create_route_step_record(route_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if get_route_payload(route_id) is None:
        return None
    values = _route_step_values_from_payload(payload)
    step = RouteStep(id=_new_id("stp"), route_definition_id=route_id, **values)
    db.session.add(step)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("步骤顺序重复") from exc
    return serialize_route_step(step)


def update_route_step_record(route_id: str, step_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if get_route_payload(route_id) is None:
        return None
    step = RouteStep.query.filter(RouteStep.id == step_id, RouteStep.route_definition_id == route_id).first()
    if step is None:
        return None
    values = _route_step_values_from_payload(payload, existing=step)
    step.step_order = values["step_order"]
    step.cell = values["cell"]
    step.action_type = values["action_type"]
    step.dwell_ms = values["dwell_ms"]
    step.rhythm_ms = values["rhythm_ms"]
    step.note = values["note"]
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("步骤顺序重复") from exc
    return serialize_route_step(step)


def delete_route_step_record(route_id: str, step_id: str) -> bool:
    if get_route_payload(route_id) is None:
        return False
    step = RouteStep.query.filter(RouteStep.id == step_id, RouteStep.route_definition_id == route_id).first()
    if step is None:
        return False
    db.session.delete(step)
    db.session.commit()
    return True


def ensure_analysis_job_stub(job_id: str, *, subject_id: str | None = None) -> AnalysisJob:
    job = AnalysisJob.query.filter(AnalysisJob.job_id == job_id).first()
    if job is None:
        job = AnalysisJob(
            job_id=job_id,
            subject_id=subject_id,
            status="done",
            progress=1.0,
            message="external report",
            analysis_profile="快速",
        )
        db.session.add(job)
        db.session.flush()
    elif subject_id and not job.subject_id:
        job.subject_id = subject_id
    return job


def create_training_video_record(
    *,
    subject_id: str,
    training_config_id: str | None = None,
    left_path: Path,
    right_path: Path,
    left_original_name: str | None,
    right_original_name: str | None,
    stereo_params_path: str | None,
    probe: dict[str, Any],
) -> str:
    training_config_id = _require_training_config(_none_if_blank(training_config_id))
    _validate_training_video_config_match(subject_id, training_config_id)
    video = TrainingVideo(
        id=_new_id("vid"),
        subject_id=subject_id,
        training_config_id=training_config_id,
        left_video_path=str(left_path),
        right_video_path=str(right_path),
        left_original_name=left_original_name,
        right_original_name=right_original_name,
        left_size_bytes=left_path.stat().st_size if left_path.exists() else None,
        right_size_bytes=right_path.stat().st_size if right_path.exists() else None,
        stereo_params_path=stereo_params_path,
        probe_json=probe,
        status="已上传",
    )
    db.session.add(video)
    db.session.commit()
    return video.id


def _training_video_values_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    subject_id = _require_active_subject(_none_if_blank(payload.get("subjectId")))
    training_config_id = _require_training_config(_none_if_blank(payload.get("trainingConfigId")))
    _validate_training_video_config_match(subject_id, training_config_id)

    left_video_path = _none_if_blank(payload.get("leftVideoPath"))
    right_video_path = _none_if_blank(payload.get("rightVideoPath"))
    if not left_video_path:
        raise ValueError("left_video_path_required")
    if not right_video_path:
        raise ValueError("right_video_path_required")

    return {
        "subject_id": subject_id,
        "training_config_id": training_config_id,
        "left_video_path": left_video_path,
        "right_video_path": right_video_path,
        "left_original_name": _none_if_blank(payload.get("leftOriginalName")),
        "right_original_name": _none_if_blank(payload.get("rightOriginalName")),
        "left_size_bytes": _int_or_none(payload.get("leftSizeBytes"), field="left_size_bytes", minimum=0),
        "right_size_bytes": _int_or_none(payload.get("rightSizeBytes"), field="right_size_bytes", minimum=0),
        "stereo_params_path": _none_if_blank(payload.get("stereoParamsPath")),
        "probe_json": payload.get("probe", payload.get("probeJson")),
        "status": _none_if_blank(payload.get("status")) or "uploaded",
    }


def create_training_video_metadata_record(payload: dict[str, Any]) -> dict[str, Any]:
    values = _training_video_values_from_payload(payload)
    video = TrainingVideo(id=_new_id("vid"), **values)
    db.session.add(video)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise InvalidReferenceError("关联数据不存在") from exc
    return serialize_training_video(video)


def serialize_training_config(config: TrainingConfig) -> dict[str, Any]:
    return {
        "id": config.id,
        "subjectId": config.subject_id,
        "footworkTypeId": config.footwork_type_id,
        "routeDefinitionId": config.route_definition_id,
        "mode": config.mode,
        "analysisProfile": config.analysis_profile,
        "lightDurationMs": config.light_duration_ms,
        "stepIntervalMs": config.step_interval_ms,
        "loopCount": config.loop_count,
        "fullTableStepCount": config.full_table_step_count,
        "hardwareFeedback": config.hardware_feedback,
        "configSnapshot": _json(config.config_snapshot),
        "createdByAccountId": config.created_by_account_id,
        "createdAt": _iso(config.created_at),
        "updatedAt": _iso(config.updated_at),
    }


def list_training_configs_page(
    *,
    keyword: str | None = None,
    subject_id: str | None = None,
    subject_ids: list[str] | None = None,
    footwork_type_id: str | None = None,
    route_definition_id: str | None = None,
    mode: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = TrainingConfig.query
    if subject_id:
        query = query.filter(TrainingConfig.subject_id == subject_id)
    if subject_ids is not None:
        query = query.filter(TrainingConfig.subject_id.in_(subject_ids))
    if footwork_type_id:
        query = query.filter(TrainingConfig.footwork_type_id == footwork_type_id)
    if route_definition_id:
        query = query.filter(TrainingConfig.route_definition_id == route_definition_id)
    if mode:
        query = query.filter(TrainingConfig.mode == mode)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                TrainingConfig.id.like(pattern),
                TrainingConfig.mode.like(pattern),
                TrainingConfig.analysis_profile.like(pattern),
            )
        )
    query = query.order_by(TrainingConfig.updated_at.desc(), TrainingConfig.created_at.desc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_training_config(row) for row in rows], total


def get_training_config_payload(config_id: str) -> dict[str, Any] | None:
    row = TrainingConfig.query.filter(TrainingConfig.id == config_id).first()
    return serialize_training_config(row) if row else None


def _validate_route_footwork_match(route_definition_id: str | None, footwork_type_id: str | None) -> None:
    if not route_definition_id or not footwork_type_id:
        return
    route = RouteDefinition.query.filter(
        RouteDefinition.id == route_definition_id,
        RouteDefinition.is_active.is_(True),
    ).first()
    if route is None:
        raise InvalidReferenceError("关联数据不存在")
    if route.footwork_type_id != footwork_type_id:
        raise InvalidReferenceError("关联数据不存在")


def _training_config_values_from_payload(
    payload: dict[str, Any],
    *,
    existing: TrainingConfig | None = None,
) -> dict[str, Any]:
    subject_id = payload.get("subjectId", existing.subject_id if existing else None)
    subject_id = _require_active_subject(_none_if_blank(subject_id))
    footwork_type_id = payload.get("footworkTypeId", existing.footwork_type_id if existing else None)
    route_definition_id = payload.get("routeDefinitionId", existing.route_definition_id if existing else None)
    footwork_type_id = _require_active_footwork_type(_none_if_blank(footwork_type_id))
    route_definition_id = _require_active_route(_none_if_blank(route_definition_id))
    _validate_route_footwork_match(route_definition_id, footwork_type_id)
    return {
        "subject_id": subject_id,
        "footwork_type_id": footwork_type_id,
        "route_definition_id": route_definition_id,
        "mode": _none_if_blank(payload.get("mode", existing.mode if existing else "练习评估")) or "练习评估",
        "analysis_profile": (
            _none_if_blank(payload.get("analysisProfile", existing.analysis_profile if existing else "快速")) or "快速"
        ),
        "light_duration_ms": _int_or_none(
            payload.get("lightDurationMs", existing.light_duration_ms if existing else None),
            field="light_duration_ms",
            minimum=0,
        ),
        "step_interval_ms": _int_or_none(
            payload.get("stepIntervalMs", existing.step_interval_ms if existing else None),
            field="step_interval_ms",
            minimum=0,
        ),
        "loop_count": _int_or_none(
            payload.get("loopCount", existing.loop_count if existing else None),
            field="loop_count",
            minimum=0,
        ),
        "full_table_step_count": _int_or_none(
            payload.get("fullTableStepCount", existing.full_table_step_count if existing else None),
            field="full_table_step_count",
            minimum=0,
        ),
        "hardware_feedback": _bool_value(
            payload.get("hardwareFeedback", existing.hardware_feedback if existing else False),
            default=False,
        ),
        "config_snapshot": payload.get("configSnapshot", existing.config_snapshot if existing else None),
        "created_by_account_id": _none_if_blank(
            payload.get("createdByAccountId", existing.created_by_account_id if existing else None)
        ),
    }


def create_training_config_record(payload: dict[str, Any]) -> dict[str, Any]:
    values = _training_config_values_from_payload(payload)
    config = TrainingConfig(id=_new_id("cfg"), **values)
    db.session.add(config)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise InvalidReferenceError("关联数据不存在") from exc
    return serialize_training_config(config)


def update_training_config_record(config_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    config = TrainingConfig.query.filter(TrainingConfig.id == config_id).first()
    if config is None:
        return None
    values = _training_config_values_from_payload(payload, existing=config)
    for key, value in values.items():
        setattr(config, key, value)
    config.updated_at = now_utc()
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise InvalidReferenceError("关联数据不存在") from exc
    return serialize_training_config(config)


def delete_training_config_record(config_id: str) -> bool:
    config = TrainingConfig.query.filter(TrainingConfig.id == config_id).first()
    if config is None:
        return False
    if (
        TrainingVideo.query.filter(TrainingVideo.training_config_id == config_id).first() is not None
        or AnalysisJob.query.filter(AnalysisJob.training_config_id == config_id).first() is not None
    ):
        raise ReferenceConflictError("被其他记录引用，无法删除")
    db.session.delete(config)
    db.session.commit()
    return True


def serialize_training_video(video: TrainingVideo) -> dict[str, Any]:
    return {
        "id": video.id,
        "subjectId": video.subject_id,
        "trainingConfigId": video.training_config_id,
        "leftVideoPath": video.left_video_path,
        "rightVideoPath": video.right_video_path,
        "leftOriginalName": video.left_original_name,
        "rightOriginalName": video.right_original_name,
        "leftSizeBytes": video.left_size_bytes,
        "rightSizeBytes": video.right_size_bytes,
        "stereoParamsPath": video.stereo_params_path,
        "probe": _json(video.probe_json),
        "status": video.status,
        "createdAt": _iso(video.created_at),
    }


def list_training_videos_page(
    *,
    keyword: str | None = None,
    subject_id: str | None = None,
    subject_ids: list[str] | None = None,
    training_config_id: str | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = TrainingVideo.query
    if subject_id:
        query = query.filter(TrainingVideo.subject_id == subject_id)
    if subject_ids is not None:
        query = query.filter(TrainingVideo.subject_id.in_(subject_ids))
    if training_config_id:
        query = query.filter(TrainingVideo.training_config_id == training_config_id)
    if status:
        query = query.filter(TrainingVideo.status == status)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                TrainingVideo.id.like(pattern),
                TrainingVideo.left_video_path.like(pattern),
                TrainingVideo.right_video_path.like(pattern),
                TrainingVideo.left_original_name.like(pattern),
                TrainingVideo.right_original_name.like(pattern),
                TrainingVideo.status.like(pattern),
            )
        )
    query = query.order_by(TrainingVideo.created_at.desc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_training_video(row) for row in rows], total


def get_training_video_payload(video_id: str) -> dict[str, Any] | None:
    row = TrainingVideo.query.filter(TrainingVideo.id == video_id).first()
    return serialize_training_video(row) if row else None


def _counts_by_column(model, column) -> dict[str, int]:
    rows = db.session.query(column, func.count(model.id)).group_by(column).all()
    return {str(value or "未设置"): int(count or 0) for value, count in rows}


def get_training_stats_payload() -> dict[str, Any]:
    return {
        "totals": {
            "trainingConfigs": TrainingConfig.query.count(),
            "trainingVideos": TrainingVideo.query.count(),
        },
        "configsByMode": _counts_by_column(TrainingConfig, TrainingConfig.mode),
        "configsByProfile": _counts_by_column(TrainingConfig, TrainingConfig.analysis_profile),
        "videosByStatus": _counts_by_column(TrainingVideo, TrainingVideo.status),
    }


def _validate_training_video_config_match(subject_id: str | None, training_config_id: str | None) -> None:
    if not subject_id or not training_config_id:
        return
    config = _get_training_config_row(training_config_id)
    if config and config.subject_id != subject_id:
        raise InvalidReferenceError("关联数据不存在")


def update_training_video_record(video_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    video = TrainingVideo.query.filter(TrainingVideo.id == video_id).first()
    if video is None:
        return None
    next_subject_id = video.subject_id
    next_training_config_id = video.training_config_id
    if "subjectId" in payload:
        next_subject_id = _require_active_subject(_none_if_blank(payload.get("subjectId")))
    if "trainingConfigId" in payload:
        next_training_config_id = _require_training_config(_none_if_blank(payload.get("trainingConfigId")))
    _validate_training_video_config_match(next_subject_id, next_training_config_id)
    video.subject_id = next_subject_id
    video.training_config_id = next_training_config_id
    if "leftVideoPath" in payload:
        video.left_video_path = _none_if_blank(payload.get("leftVideoPath")) or video.left_video_path
    if "rightVideoPath" in payload:
        video.right_video_path = _none_if_blank(payload.get("rightVideoPath")) or video.right_video_path
    if "leftOriginalName" in payload:
        video.left_original_name = _none_if_blank(payload.get("leftOriginalName"))
    if "rightOriginalName" in payload:
        video.right_original_name = _none_if_blank(payload.get("rightOriginalName"))
    if "leftSizeBytes" in payload:
        video.left_size_bytes = _int_or_none(payload.get("leftSizeBytes"), field="left_size_bytes", minimum=0)
    if "rightSizeBytes" in payload:
        video.right_size_bytes = _int_or_none(payload.get("rightSizeBytes"), field="right_size_bytes", minimum=0)
    if "stereoParamsPath" in payload:
        video.stereo_params_path = _none_if_blank(payload.get("stereoParamsPath"))
    if "probe" in payload:
        video.probe_json = payload.get("probe")
    if "probeJson" in payload:
        video.probe_json = payload.get("probeJson")
    if "status" in payload:
        video.status = _none_if_blank(payload.get("status")) or video.status
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise InvalidReferenceError("关联数据不存在") from exc
    return serialize_training_video(video)


def delete_training_video_record(video_id: str) -> bool:
    video = TrainingVideo.query.filter(TrainingVideo.id == video_id).first()
    if video is None:
        return False
    if (
        AnalysisJob.query.filter(AnalysisJob.training_video_id == video_id).first() is not None
        or KinematicsDataset.query.filter(KinematicsDataset.training_video_id == video_id).first() is not None
    ):
        raise ReferenceConflictError("被其他记录引用，无法删除")
    db.session.delete(video)
    db.session.commit()
    return True


def upsert_analysis_job_from_record(record: Any) -> None:
    meta = record.meta if isinstance(getattr(record, "meta", None), dict) else {}
    job = AnalysisJob.query.filter(AnalysisJob.job_id == record.job_id).first()
    if job is None:
        job = AnalysisJob(job_id=record.job_id)
        db.session.add(job)
    job.status = record.status
    job.stage = record.stage
    job.progress = float(record.progress or 0.0)
    job.message = record.message
    job.error = record.error
    job.error_code = record.error_code
    job.fps = float(record.fps or 60.0)
    job.subject_id = meta.get("user_id") or job.subject_id
    job.training_video_id = meta.get("training_video_id") or job.training_video_id
    job.training_config_id = meta.get("training_config_id") or job.training_config_id
    job.analysis_profile = meta.get("analysis_profile") or job.analysis_profile or "快速"
    job.input_probe_json = meta.get("input_probe")
    job.estimated_duration_s = meta.get("estimated_duration_s")
    job.stereo_params_path = meta.get("stereo_params_override")
    job.step_display_name = meta.get("step_display_name")
    job.report_mode = meta.get("report_mode") or "eval"
    job.result_id = meta.get("result_id") or job.result_id
    job.meta_json = meta
    try:
        if getattr(record, "created_at", None):
            job.created_at = datetime.fromisoformat(str(record.created_at).replace("Z", "+00:00"))
        if getattr(record, "updated_at", None):
            job.updated_at = datetime.fromisoformat(str(record.updated_at).replace("Z", "+00:00"))
    except ValueError:
        job.updated_at = now_utc()
    if record.status in ("done", "failed"):
        job.completed_at = job.completed_at or now_utc()
    db.session.commit()


def upsert_kinematics_dataset_for_job(
    *,
    job_id: str,
    subject_id: str | None,
    training_video_id: str | None,
    report_path: Path,
    chart_bundle_path: Path,
    kinematics_dir: Path,
    payload: dict[str, Any],
    synced_left_path: Path | None = None,
    synced_right_path: Path | None = None,
) -> str:
    job = ensure_analysis_job_stub(job_id, subject_id=subject_id)
    job.report_payload_path = str(report_path)
    job.chart_bundle_path = str(chart_bundle_path)
    job.kinematics_dir = str(kinematics_dir)
    dataset = KinematicsDataset.query.filter(KinematicsDataset.job_id == job_id).first()
    if dataset is None:
        dataset = KinematicsDataset(id=_new_id("kin"), job_id=job_id)
        db.session.add(dataset)
    dataset.subject_id = subject_id
    dataset.training_video_id = training_video_id
    dataset.report_payload_path = str(report_path)
    dataset.chart_bundle_path = str(chart_bundle_path)
    if synced_left_path is not None:
        dataset.synced_left_path = str(synced_left_path)
    if synced_right_path is not None:
        dataset.synced_right_path = str(synced_right_path)
    dataset.frame_csv_path = str(kinematics_dir / "frame_metrics.csv")
    dataset.session_csv_path = str(kinematics_dir / "session_summary.csv")
    dataset.step_csv_path = str(kinematics_dir / "step_metrics.csv")
    dataset.unit_csv_path = str(kinematics_dir / "unit_metrics.csv")
    dataset.summary_json = payload.get("summaryMetrics") or {}
    dataset.derived_stats_json = payload.get("derivedStats") or {}
    dataset.quality_flags_json = payload.get("qualityFlags") or {}
    db.session.flush()
    _replace_frame_metrics_from_csv(dataset.id, Path(dataset.frame_csv_path))
    db.session.commit()
    return dataset.id


def delete_kinematics_dataset(dataset_id: str) -> bool:
    """删除运动学数据集（含帧指标），解除关联评估记录的引用。"""
    dataset = KinematicsDataset.query.filter(KinematicsDataset.id == dataset_id).first()
    if dataset is None:
        return False
    EvaluationRecord.query.filter(
        EvaluationRecord.kinematics_dataset_id == dataset_id
    ).update({"kinematics_dataset_id": None})
    KinematicsFrameMetric.query.filter(
        KinematicsFrameMetric.dataset_id == dataset_id
    ).delete()
    db.session.delete(dataset)
    db.session.commit()
    return True


def _row_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row.get(key)
    return None


def _csv_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _csv_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _replace_frame_metrics_from_csv(dataset_id: str, csv_path: Path) -> int:
    KinematicsFrameMetric.query.filter(KinematicsFrameMetric.dataset_id == dataset_id).delete()
    if not csv_path.exists():
        return 0

    # SQLite 的 BigInteger 不支持 autoincrement，需手动分配 ID
    next_id = (db.session.query(func.max(KinematicsFrameMetric.id)).scalar() or 0) + 1
    metrics: list[KinematicsFrameMetric] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            frame_index = _csv_int(_row_value(row, "frame_index", "frame_id", "frame"))
            if frame_index is None:
                continue
            metrics.append(
                KinematicsFrameMetric(
                    id=next_id,
                    dataset_id=dataset_id,
                    frame_index=frame_index,
                    time_s=_csv_float(_row_value(row, "time_s", "timestamp_s", "time")),
                    com_speed_mps=_csv_float(_row_value(row, "com_speed_mps")),
                    com_acceleration_mps2=_csv_float(_row_value(row, "com_acceleration_mps2")),
                    turning_speed_deg_s=_csv_float(_row_value(row, "turning_speed_deg_s")),
                    left_knee_angle_deg=_csv_float(_row_value(row, "left_knee_angle_deg")),
                    right_knee_angle_deg=_csv_float(_row_value(row, "right_knee_angle_deg")),
                    left_ankle_angle_deg=_csv_float(_row_value(row, "left_ankle_angle_deg")),
                    right_ankle_angle_deg=_csv_float(_row_value(row, "right_ankle_angle_deg")),
                )
            )
            next_id += 1
    if metrics:
        db.session.add_all(metrics)
    return len(metrics)


def _grade_from_score(score: int | None) -> str | None:
    if score is None:
        return None
    if score >= 90:
        return "优秀"
    if score >= 75:
        return "良好"
    if score >= 60:
        return "合格"
    return "待提高"


def serialize_kinematics_dataset(dataset: KinematicsDataset) -> dict[str, Any]:
    # JOIN 查询人类可读字段
    subject_name = None
    if dataset.subject_id:
        subj = db.session.get(Subject, dataset.subject_id)
        if subj:
            subject_name = subj.name

    job = None
    if dataset.job_id:
        job = db.session.get(AnalysisJob, dataset.job_id)

    video = None
    if dataset.training_video_id:
        video = db.session.get(TrainingVideo, dataset.training_video_id)

    evaluation = EvaluationRecord.query.filter(
        EvaluationRecord.kinematics_dataset_id == dataset.id,
    ).first()

    return {
        "id": dataset.id,
        "jobId": dataset.job_id,
        "subjectId": dataset.subject_id,
        "subjectName": subject_name or "未知受试者",
        "stepName": (job.step_display_name if job and job.step_display_name else "未命名"),
        "mode": (job.report_mode if job else None),
        "profile": (job.analysis_profile if job else None),
        "score": evaluation.score if evaluation else None,
        "grade": (evaluation.grade if evaluation else "未评估"),
        "leftVideoName": (video.left_original_name if video else None),
        "rightVideoName": (video.right_original_name if video else None),
        "trainingVideoId": dataset.training_video_id,
        "reportPayloadPath": dataset.report_payload_path,
        "chartBundlePath": dataset.chart_bundle_path,
        "frameCsvPath": dataset.frame_csv_path,
        "sessionCsvPath": dataset.session_csv_path,
        "stepCsvPath": dataset.step_csv_path,
        "unitCsvPath": dataset.unit_csv_path,
        "syncedLeftVideoUrl": f"/api/v1/kinematics-datasets/{dataset.id}/synced-video/left" if dataset.synced_left_path else None,
        "syncedRightVideoUrl": f"/api/v1/kinematics-datasets/{dataset.id}/synced-video/right" if dataset.synced_right_path else None,
        "summary": _json(dataset.summary_json),
        "derivedStats": _json(dataset.derived_stats_json),
        "qualityFlags": _json(dataset.quality_flags_json),
        "createdAt": _iso(dataset.created_at),
    }


def list_kinematics_datasets_page(
    *,
    keyword: str | None = None,
    subject_id: str | None = None,
    subject_ids: list[str] | None = None,
    job_id: str | None = None,
    training_video_id: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = KinematicsDataset.query
    if subject_id:
        query = query.filter(KinematicsDataset.subject_id == subject_id)
    if subject_ids is not None:
        query = query.filter(KinematicsDataset.subject_id.in_(subject_ids))
    if job_id:
        query = query.filter(KinematicsDataset.job_id == job_id)
    if training_video_id:
        query = query.filter(KinematicsDataset.training_video_id == training_video_id)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                KinematicsDataset.id.like(pattern),
                KinematicsDataset.job_id.like(pattern),
                KinematicsDataset.report_payload_path.like(pattern),
                KinematicsDataset.chart_bundle_path.like(pattern),
                KinematicsDataset.frame_csv_path.like(pattern),
                KinematicsDataset.session_csv_path.like(pattern),
                KinematicsDataset.step_csv_path.like(pattern),
                KinematicsDataset.unit_csv_path.like(pattern),
            )
        )
    query = query.order_by(KinematicsDataset.created_at.desc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_kinematics_dataset(row) for row in rows], total


def get_kinematics_dataset_payload(dataset_id: str) -> dict[str, Any] | None:
    row = KinematicsDataset.query.filter(KinematicsDataset.id == dataset_id).first()
    return serialize_kinematics_dataset(row) if row else None


def serialize_kinematics_frame_metric(metric: KinematicsFrameMetric) -> dict[str, Any]:
    return {
        "id": metric.id,
        "datasetId": metric.dataset_id,
        "frameIndex": metric.frame_index,
        "timeS": metric.time_s,
        "comSpeedMps": metric.com_speed_mps,
        "comAccelerationMps2": metric.com_acceleration_mps2,
        "turningSpeedDegS": metric.turning_speed_deg_s,
        "leftKneeAngleDeg": metric.left_knee_angle_deg,
        "rightKneeAngleDeg": metric.right_knee_angle_deg,
        "leftAnkleAngleDeg": metric.left_ankle_angle_deg,
        "rightAnkleAngleDeg": metric.right_ankle_angle_deg,
    }


def list_kinematics_metrics_page(
    dataset_id: str,
    *,
    frame_index_from: int | None = None,
    frame_index_to: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int] | None:
    if KinematicsDataset.query.filter(KinematicsDataset.id == dataset_id).first() is None:
        return None
    query = KinematicsFrameMetric.query.filter(KinematicsFrameMetric.dataset_id == dataset_id)
    if frame_index_from is not None:
        query = query.filter(KinematicsFrameMetric.frame_index >= frame_index_from)
    if frame_index_to is not None:
        query = query.filter(KinematicsFrameMetric.frame_index <= frame_index_to)
    query = query.order_by(KinematicsFrameMetric.frame_index.asc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_kinematics_frame_metric(row) for row in rows], total


def serialize_evaluation(evaluation: EvaluationRecord) -> dict[str, Any]:
    return {
        "id": evaluation.id,
        "subjectId": evaluation.subject_id,
        "analysisJobId": evaluation.analysis_job_id,
        "kinematicsDatasetId": evaluation.kinematics_dataset_id,
        "footworkTypeId": evaluation.footwork_type_id,
        "routeDefinitionId": evaluation.route_definition_id,
        "score": evaluation.score,
        "grade": evaluation.grade,
        "summary": _json(evaluation.summary_json),
        "suggestions": _json(evaluation.suggestions_json),
        "createdByAccountId": evaluation.created_by_account_id,
        "createdAt": _iso(evaluation.created_at),
    }


def list_evaluations_page(
    *,
    keyword: str | None = None,
    subject_id: str | None = None,
    subject_ids: list[str] | None = None,
    analysis_job_id: str | None = None,
    kinematics_dataset_id: str | None = None,
    footwork_type_id: str | None = None,
    route_definition_id: str | None = None,
    grade: str | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = EvaluationRecord.query
    if subject_id:
        query = query.filter(EvaluationRecord.subject_id == subject_id)
    if subject_ids is not None:
        query = query.filter(EvaluationRecord.subject_id.in_(subject_ids))
    if analysis_job_id:
        query = query.filter(EvaluationRecord.analysis_job_id == analysis_job_id)
    if kinematics_dataset_id:
        query = query.filter(EvaluationRecord.kinematics_dataset_id == kinematics_dataset_id)
    if footwork_type_id:
        query = query.filter(EvaluationRecord.footwork_type_id == footwork_type_id)
    if route_definition_id:
        query = query.filter(EvaluationRecord.route_definition_id == route_definition_id)
    if grade:
        query = query.filter(EvaluationRecord.grade == grade)
    if min_score is not None:
        query = query.filter(EvaluationRecord.score >= min_score)
    if max_score is not None:
        query = query.filter(EvaluationRecord.score <= max_score)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                EvaluationRecord.id.like(pattern),
                EvaluationRecord.analysis_job_id.like(pattern),
                EvaluationRecord.grade.like(pattern),
            )
        )
    query = query.order_by(EvaluationRecord.created_at.desc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_evaluation(row) for row in rows], total


def get_evaluation_payload(evaluation_id: str) -> dict[str, Any] | None:
    row = EvaluationRecord.query.filter(EvaluationRecord.id == evaluation_id).first()
    return serialize_evaluation(row) if row else None


def _score_from_payload(payload: dict[str, Any], *, existing: EvaluationRecord | None = None) -> int | None:
    if "score" not in payload:
        return existing.score if existing else None
    return _int_or_none(payload.get("score"), field="score", minimum=0, maximum=100)


def _validate_video_subject(video_id: str | None, subject_id: str | None) -> None:
    if not video_id or not subject_id:
        return
    video = TrainingVideo.query.filter(TrainingVideo.id == video_id).first()
    if video is None:
        raise InvalidReferenceError("关联数据不存在")
    if video.subject_id != subject_id:
        raise InvalidReferenceError("关联数据不存在")


def _validate_evaluation_reference_graph(
    *,
    subject_id: str,
    analysis_job_id: str | None,
    kinematics_dataset_id: str | None,
    footwork_type_id: str | None,
    route_definition_id: str | None,
) -> None:
    job = _get_analysis_job_row(analysis_job_id)
    dataset = _get_kinematics_dataset_row(kinematics_dataset_id)
    _validate_route_footwork_match(route_definition_id, footwork_type_id)

    if job and job.subject_id and job.subject_id != subject_id:
        raise InvalidReferenceError("关联数据不存在")
    if dataset:
        if dataset.subject_id != subject_id:
            raise InvalidReferenceError("关联数据不存在")
        if analysis_job_id and dataset.job_id != analysis_job_id:
            raise InvalidReferenceError("关联数据不存在")
        _validate_video_subject(dataset.training_video_id, subject_id)

    if job:
        _validate_video_subject(job.training_video_id, subject_id)
        if dataset and job.training_video_id and dataset.training_video_id and job.training_video_id != dataset.training_video_id:
            raise InvalidReferenceError("关联数据不存在")
        if job.training_config_id:
            config = _get_training_config_row(job.training_config_id)
            if config and config.subject_id != subject_id:
                raise InvalidReferenceError("关联数据不存在")
            if (
                config
                and footwork_type_id
                and config.footwork_type_id
                and config.footwork_type_id != footwork_type_id
            ):
                raise InvalidReferenceError("关联数据不存在")
            if (
                config
                and route_definition_id
                and config.route_definition_id
                and config.route_definition_id != route_definition_id
            ):
                raise InvalidReferenceError("关联数据不存在")


def _evaluation_values_from_payload(
    payload: dict[str, Any],
    *,
    existing: EvaluationRecord | None = None,
) -> dict[str, Any]:
    subject_id = payload.get("subjectId", existing.subject_id if existing else None)
    subject_id = _require_active_subject(_none_if_blank(subject_id))
    analysis_job_id = _require_analysis_job(
        _none_if_blank(payload.get("analysisJobId", existing.analysis_job_id if existing else None))
    )
    kinematics_dataset_id = _require_kinematics_dataset(
        _none_if_blank(payload.get("kinematicsDatasetId", existing.kinematics_dataset_id if existing else None))
    )
    footwork_type_id = _require_active_footwork_type(
        _none_if_blank(payload.get("footworkTypeId", existing.footwork_type_id if existing else None))
    )
    route_definition_id = _require_active_route(
        _none_if_blank(payload.get("routeDefinitionId", existing.route_definition_id if existing else None))
    )
    _validate_evaluation_reference_graph(
        subject_id=subject_id,
        analysis_job_id=analysis_job_id,
        kinematics_dataset_id=kinematics_dataset_id,
        footwork_type_id=footwork_type_id,
        route_definition_id=route_definition_id,
    )
    score = _score_from_payload(payload, existing=existing)
    if "score" in payload or "grade" not in payload:
        grade = _grade_from_score(score)
    else:
        grade = _none_if_blank(payload.get("grade", existing.grade if existing else None))
    return {
        "subject_id": subject_id,
        "analysis_job_id": analysis_job_id,
        "kinematics_dataset_id": kinematics_dataset_id,
        "footwork_type_id": footwork_type_id,
        "route_definition_id": route_definition_id,
        "score": score,
        "grade": grade,
        "summary_json": payload.get("summary", existing.summary_json if existing else None),
        "suggestions_json": payload.get("suggestions", existing.suggestions_json if existing else None),
        "created_by_account_id": _none_if_blank(
            payload.get("createdByAccountId", existing.created_by_account_id if existing else None)
        ),
    }


def create_evaluation_record(payload: dict[str, Any]) -> dict[str, Any]:
    values = _evaluation_values_from_payload(payload)
    evaluation = EvaluationRecord(id=_new_id("eval"), **values)
    db.session.add(evaluation)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise InvalidReferenceError("关联数据不存在") from exc
    return serialize_evaluation(evaluation)


def update_evaluation_record(evaluation_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    evaluation = EvaluationRecord.query.filter(EvaluationRecord.id == evaluation_id).first()
    if evaluation is None:
        return None
    values = _evaluation_values_from_payload(payload, existing=evaluation)
    for key, value in values.items():
        setattr(evaluation, key, value)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise InvalidReferenceError("关联数据不存在") from exc
    return serialize_evaluation(evaluation)


def delete_evaluation_record(evaluation_id: str) -> bool:
    evaluation = EvaluationRecord.query.filter(EvaluationRecord.id == evaluation_id).first()
    if evaluation is None:
        return False
    Report.query.filter(Report.evaluation_record_id == evaluation_id).update({"evaluation_record_id": None})
    db.session.delete(evaluation)
    db.session.commit()
    return True


def upsert_evaluation_and_report(
    *,
    subject_id: str,
    job_id: str,
    mode: str,
    step_name: str | None,
    summary: dict[str, Any],
) -> str | None:
    if not isinstance(summary, dict):
        summary = {}
    subject = Subject.query.filter(Subject.id == subject_id, Subject.is_active.is_(True)).first()
    if subject is None:
        return None
    ensure_analysis_job_stub(job_id, subject_id=subject_id)
    dataset = KinematicsDataset.query.filter(KinematicsDataset.job_id == job_id).first()
    report = Report.query.filter(Report.subject_id == subject_id, Report.job_id == job_id).first()
    score_raw = summary.get("score")
    try:
        score = int(score_raw) if score_raw not in (None, "") else None
    except (TypeError, ValueError):
        score = None
    if report and report.evaluation_record_id:
        evaluation = EvaluationRecord.query.filter(EvaluationRecord.id == report.evaluation_record_id).first()
    else:
        evaluation = None
    if evaluation is None:
        evaluation = EvaluationRecord(
            id=_new_id("eval"),
            subject_id=subject_id,
            analysis_job_id=job_id,
        )
        db.session.add(evaluation)
    evaluation.kinematics_dataset_id = dataset.id if dataset else None
    evaluation.score = score
    evaluation.grade = _grade_from_score(score)
    evaluation.summary_json = summary
    evaluation.suggestions_json = {}

    completed_at = now_utc()
    if report is None:
        report = Report(id=_new_id("rpt"), subject_id=subject_id, job_id=job_id)
        db.session.add(report)
    report.evaluation_record_id = evaluation.id
    report.completed_at = completed_at
    report.mode = str(mode or "eval").strip() or "eval"
    report.step_name = str(step_name or "视频分析").strip()[:120] or "视频分析"
    report.summary_json = summary
    db.session.commit()
    return report.id


def serialize_report(report: Report, *, include_user_name: bool = False) -> dict[str, Any]:
    out = {
        "id": report.id,
        "userId": report.subject_id,
        "jobId": report.job_id,
        "completedAt": _iso(report.completed_at),
        "mode": report.mode,
        "stepName": report.step_name,
        "summary": _json(report.summary_json),
    }
    if include_user_name:
        subject = Subject.query.filter(Subject.id == report.subject_id).first()
        out["userName"] = subject.name if subject else None
    return out


def list_reports_for_subject(
    *,
    subject_id: str,
    mode: str | None,
    start_date: str | None,
    end_date: str | None,
    step_name: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    query = Report.query.filter(Report.subject_id == subject_id)
    if mode:
        query = query.filter(Report.mode == mode)
    if start_date:
        query = query.filter(Report.completed_at >= start_date)
    if end_date:
        query = query.filter(Report.completed_at <= end_date)
    if step_name:
        query = query.filter(Report.step_name.like(f"%{step_name}%"))
    total = query.count()
    rows = query.order_by(Report.completed_at.desc()).limit(limit).offset(offset).all()
    return [serialize_report(row) for row in rows], total


def get_report_payload(report_id: str) -> dict[str, Any] | None:
    report = Report.query.filter(Report.id == report_id).first()
    return serialize_report(report) if report else None


def delete_report_record(report_id: str) -> bool:
    report = Report.query.filter(Report.id == report_id).first()
    if report is None:
        return False
    db.session.delete(report)
    db.session.commit()
    return True


def compare_report_records(report_ids: list[str]) -> list[dict[str, Any]]:
    if not report_ids:
        return []
    rows = Report.query.filter(Report.id.in_(report_ids)).all()
    by_id = {row.id: row for row in rows}
    return [serialize_report(by_id[rid], include_user_name=True) for rid in report_ids if rid in by_id]


def save_analysis_result_record(
    *,
    result_id: str,
    job_id: str,
    payload: dict[str, Any],
    job_meta: dict[str, Any],
    report_path: Path | None,
) -> None:
    result = AnalysisResult.query.filter(AnalysisResult.result_id == result_id).first()
    if result is None:
        result = AnalysisResult(result_id=result_id, job_id=job_id)
        db.session.add(result)
    result.profile_json = (job_meta or {}).get("profile") or {}
    result.summary_metrics_json = payload.get("summaryMetrics") or {}
    result.derived_stats_json = payload.get("derivedStats") or {}
    result.report_path = str(report_path) if report_path else None
    db.session.commit()


def list_analysis_result_records(*, limit: int) -> list[dict[str, Any]]:
    rows = AnalysisResult.query.order_by(AnalysisResult.saved_at.desc()).limit(max(1, int(limit))).all()
    return [
        {
            "resultId": row.result_id,
            "jobId": row.job_id,
            "savedAt": _iso(row.saved_at),
            "profile": _json(row.profile_json),
            "summaryMetrics": _json(row.summary_metrics_json),
            "derivedStats": _json(row.derived_stats_json),
        }
        for row in rows
    ]


def get_analysis_result_record(result_id: str) -> dict[str, Any] | None:
    row = AnalysisResult.query.filter(AnalysisResult.result_id == result_id).first()
    if row is None:
        return None
    item = {
        "resultId": row.result_id,
        "jobId": row.job_id,
        "savedAt": _iso(row.saved_at),
        "profile": _json(row.profile_json),
        "summaryMetrics": _json(row.summary_metrics_json),
        "derivedStats": _json(row.derived_stats_json),
        "reportPath": row.report_path,
        "payload": None,
    }
    if row.report_path:
        path = Path(row.report_path)
        if path.exists():
            try:
                item["payload"] = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                item["payload"] = None
    return item


def serialize_account(row: Account) -> dict[str, Any]:
    return {
        "id": row.id,
        "account": row.account,
        "username": row.username,
        "status": row.status,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


def serialize_role(row: Role) -> dict[str, Any]:
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "createdAt": _iso(row.created_at),
    }


def serialize_permission(row: Permission) -> dict[str, Any]:
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "createdAt": _iso(row.created_at),
    }


def list_accounts_page(
    *,
    keyword: str | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = Account.query
    if status:
        query = query.filter(Account.status == status.strip())
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(Account.account.like(pattern), Account.username.like(pattern)))
    query = query.order_by(Account.created_at.desc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_account(row) for row in rows], total


def get_account_payload(account_id: str) -> dict[str, Any] | None:
    row = Account.query.filter(Account.id == account_id).first()
    return serialize_account(row) if row else None


def _account_values_from_payload(payload: dict[str, Any], *, existing: Account | None = None) -> dict[str, Any]:
    account = str(payload.get("account", existing.account if existing else "") or "").strip()
    username = _clean_text(payload.get("username", existing.username if existing else ""))
    status = str(payload.get("status", existing.status if existing else "active") or "active").strip()
    if not account:
        raise ValueError("请填写账号")
    if not username:
        raise ValueError("请填写用户名")
    if not status:
        raise ValueError("请填写状态")

    # Password handling: only for new accounts, hash via PBKDF2; updates never touch password_hash
    raw_password = str(payload.get("passwordHash") or "").strip()
    if existing is None:
        # New account — require initial password
        if not raw_password:
            raise ValueError("请填写密码")
        password_hash = hash_password(raw_password)
    else:
        # Update — keep existing password_hash unchanged
        password_hash = existing.password_hash

    return {
        "account": account,
        "password_hash": password_hash,
        "username": username,
        "status": status,
    }


def _ensure_account_available(*, account_id: str | None, account: str) -> None:
    query = Account.query.filter(Account.account == account)
    if account_id:
        query = query.filter(Account.id != account_id)
    if query.first() is not None:
        raise DuplicateRecordError("账号已存在")


def create_account_record(payload: dict[str, Any]) -> dict[str, Any]:
    values = _account_values_from_payload(payload)
    _ensure_account_available(account_id=None, account=values["account"])
    row = Account(id=_new_id("acct"), **values)
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("账号已存在") from exc
    return serialize_account(row)


def update_account_record(account_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    row = Account.query.filter(Account.id == account_id).first()
    if row is None:
        return None
    values = _account_values_from_payload(payload, existing=row)
    _ensure_account_available(account_id=account_id, account=values["account"])
    for key, value in values.items():
        setattr(row, key, value)
    row.updated_at = now_utc()
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("账号已存在") from exc
    return serialize_account(row)


def delete_account_record(account_id: str) -> bool:
    row = Account.query.filter(Account.id == account_id).first()
    if row is None:
        return False
    # 级联软删该账号创建的所有受试者
    subjects = Subject.query.filter(
        Subject.created_by_account_id == account_id,
        Subject.is_active.is_(True),
    ).all()
    for sub in subjects:
        apply_soft_delete(sub)
    AccountRole.query.filter(AccountRole.account_id == account_id).delete()
    db.session.delete(row)
    db.session.commit()
    return True


def list_roles_page(
    *,
    keyword: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = Role.query
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(Role.code.like(pattern), Role.name.like(pattern)))
    query = query.order_by(Role.code.asc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_role(row) for row in rows], total


def get_role_payload(role_id: str) -> dict[str, Any] | None:
    row = Role.query.filter(Role.id == role_id).first()
    return serialize_role(row) if row else None


def _role_values_from_payload(payload: dict[str, Any], *, existing: Role | None = None) -> dict[str, Any]:
    code = str(payload.get("code", existing.code if existing else "") or "").strip().lower()
    name = _clean_text(payload.get("name", existing.name if existing else ""))
    if not code:
        raise ValueError("请填写编码")
    if not name:
        raise ValueError("请填写名称")
    return {"code": code, "name": name}


def _ensure_role_code_available(*, role_id: str | None, code: str) -> None:
    query = Role.query.filter(Role.code == code)
    if role_id:
        query = query.filter(Role.id != role_id)
    if query.first() is not None:
        raise DuplicateRecordError("编码已存在")


def create_role_record(payload: dict[str, Any]) -> dict[str, Any]:
    values = _role_values_from_payload(payload)
    _ensure_role_code_available(role_id=None, code=values["code"])
    row = Role(id=_new_id("role"), **values)
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("编码已存在") from exc
    return serialize_role(row)


def update_role_record(role_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    row = Role.query.filter(Role.id == role_id).first()
    if row is None:
        return None
    values = _role_values_from_payload(payload, existing=row)
    _ensure_role_code_available(role_id=role_id, code=values["code"])
    for key, value in values.items():
        setattr(row, key, value)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("编码已存在") from exc
    return serialize_role(row)


def delete_role_record(role_id: str) -> bool:
    row = Role.query.filter(Role.id == role_id).first()
    if row is None:
        return False
    if AccountRole.query.filter(AccountRole.role_id == role_id).first() is not None:
        raise ReferenceConflictError("被其他记录引用，无法删除")
    if RolePermission.query.filter(RolePermission.role_id == role_id).first() is not None:
        raise ReferenceConflictError("被其他记录引用，无法删除")
    db.session.delete(row)
    db.session.commit()
    return True


def list_permissions_page(
    *,
    keyword: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = Permission.query
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(Permission.code.like(pattern), Permission.name.like(pattern)))
    query = query.order_by(Permission.code.asc())
    rows, total = paginate_query(query, limit=limit, offset=offset)
    return [serialize_permission(row) for row in rows], total


def get_permission_payload(permission_id: str) -> dict[str, Any] | None:
    row = Permission.query.filter(Permission.id == permission_id).first()
    return serialize_permission(row) if row else None


def _permission_values_from_payload(
    payload: dict[str, Any],
    *,
    existing: Permission | None = None,
) -> dict[str, Any]:
    code = str(payload.get("code", existing.code if existing else "") or "").strip().lower()
    name = _clean_text(payload.get("name", existing.name if existing else ""))
    if not code:
        raise ValueError("请填写编码")
    if not name:
        raise ValueError("请填写名称")
    return {"code": code, "name": name}


def _ensure_permission_code_available(*, permission_id: str | None, code: str) -> None:
    query = Permission.query.filter(Permission.code == code)
    if permission_id:
        query = query.filter(Permission.id != permission_id)
    if query.first() is not None:
        raise DuplicateRecordError("编码已存在")


def create_permission_record(payload: dict[str, Any]) -> dict[str, Any]:
    values = _permission_values_from_payload(payload)
    _ensure_permission_code_available(permission_id=None, code=values["code"])
    row = Permission(id=_new_id("perm"), **values)
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("编码已存在") from exc
    return serialize_permission(row)


def update_permission_record(permission_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    row = Permission.query.filter(Permission.id == permission_id).first()
    if row is None:
        return None
    values = _permission_values_from_payload(payload, existing=row)
    _ensure_permission_code_available(permission_id=permission_id, code=values["code"])
    for key, value in values.items():
        setattr(row, key, value)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise DuplicateRecordError("编码已存在") from exc
    return serialize_permission(row)


def delete_permission_record(permission_id: str) -> bool:
    row = Permission.query.filter(Permission.id == permission_id).first()
    if row is None:
        return False
    if RolePermission.query.filter(RolePermission.permission_id == permission_id).first() is not None:
        raise ReferenceConflictError("被其他记录引用，无法删除")
    db.session.delete(row)
    db.session.commit()
    return True


def _unique_text_ids(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"invalid_{field}")
    ids: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if not text:
            raise ValueError(f"invalid_{field}")
        if text not in seen:
            seen.add(text)
            ids.append(text)
    return ids


def list_roles_for_account(account_id: str) -> tuple[list[dict[str, Any]], int] | None:
    if Account.query.filter(Account.id == account_id).first() is None:
        return None
    query = (
        Role.query.join(AccountRole, AccountRole.role_id == Role.id)
        .filter(AccountRole.account_id == account_id)
        .order_by(Role.code.asc())
    )
    rows = query.all()
    return [serialize_role(row) for row in rows], len(rows)


def replace_account_roles(account_id: str, payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int] | None:
    if Account.query.filter(Account.id == account_id).first() is None:
        return None
    role_ids = _unique_text_ids(payload.get("roleIds"), field="role_ids")
    count = Role.query.filter(Role.id.in_(role_ids)).count() if role_ids else 0
    if count != len(role_ids):
        raise InvalidReferenceError("关联数据不存在")
    AccountRole.query.filter(AccountRole.account_id == account_id).delete()
    for role_id in role_ids:
        db.session.add(AccountRole(account_id=account_id, role_id=role_id))
    db.session.commit()
    return list_roles_for_account(account_id)


def list_permissions_for_role(role_id: str) -> tuple[list[dict[str, Any]], int] | None:
    if Role.query.filter(Role.id == role_id).first() is None:
        return None
    query = (
        Permission.query.join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == role_id)
        .order_by(Permission.code.asc())
    )
    rows = query.all()
    return [serialize_permission(row) for row in rows], len(rows)


def replace_role_permissions(role_id: str, payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int] | None:
    if Role.query.filter(Role.id == role_id).first() is None:
        return None
    permission_ids = _unique_text_ids(payload.get("permissionIds"), field="permission_ids")
    count = Permission.query.filter(Permission.id.in_(permission_ids)).count() if permission_ids else 0
    if count != len(permission_ids):
        raise InvalidReferenceError("关联数据不存在")
    RolePermission.query.filter(RolePermission.role_id == role_id).delete()
    for permission_id in permission_ids:
        db.session.add(RolePermission(role_id=role_id, permission_id=permission_id))
    db.session.commit()
    return list_permissions_for_role(role_id)
