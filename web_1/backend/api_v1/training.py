"""Training configs and videos API."""

from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy import or_

from backend import repositories as repo
from backend.api_utils import get_account_id_from_headers as _account_id, json_err, json_ok, list_response, parse_pagination


def _json_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None
    return payload


def _account_subject_ids() -> list[str] | None:
    aid = _account_id()
    if not aid:
        return None
    return repo._subject_ids_for_account(aid)  # 空列表→无数据，正确


def _check_ownership(subject_id: str) -> bool | None:
    """True=owned, False=other account, None=not found"""
    aid = _account_id()
    if not aid:
        return True  # no header → allow (backward compat)
    return repo.check_subject_ownership(subject_id, aid)


def register(bp: Blueprint) -> None:
    @bp.get("/training-stats")
    def get_training_stats():
        return json_ok(item=repo.get_training_stats_payload())

    @bp.get("/training-configs")
    def list_training_configs():
        page = parse_pagination(request.args, default_limit=30)
        sid = (request.args.get("subjectId") or request.args.get("subject_id") or "").strip() or None
        fid = (request.args.get("footworkTypeId") or request.args.get("footwork_type_id") or "").strip() or None
        rid = (request.args.get("routeDefinitionId") or request.args.get("route_definition_id") or "").strip() or None
        mode = (request.args.get("mode") or "").strip() or None
        sort_by = (request.args.get("sortBy") or "").strip() or None
        sort_order = (request.args.get("sortOrder") or "asc").strip()
        items, total = repo.list_training_configs_page(
            keyword=page.keyword,
            subject_id=sid,
            subject_ids=_account_subject_ids(),
            footwork_type_id=fid,
            route_definition_id=rid,
            mode=mode,
            limit=page.limit,
            offset=page.offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        base = repo.TrainingConfig.query
        if page.keyword:
            pattern = f"%{page.keyword.strip()}%"
            base = base.filter(or_(
                repo.TrainingConfig.id.like(pattern),
                repo.TrainingConfig.mode.like(pattern),
                repo.TrainingConfig.analysis_profile.like(pattern),
            ))
        filters_data = repo.build_filter_aggregation(
            base, repo.TrainingConfig, "training-configs",
            {"subjectId": sid, "footworkTypeId": fid, "routeDefinitionId": rid, "mode": mode},
        )

        return list_response(items, total=total, limit=page.limit, offset=page.offset,
                            extra={"filters": filters_data})

    @bp.post("/training-configs")
    def create_training_config():
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        sid = payload.get("subjectId") or payload.get("subject_id")
        if sid:
            ok = _check_ownership(sid)
            if ok is None:
                return json_err("subject_not_found", 404)
            if not ok:
                return json_err("permission_denied", 403)
        try:
            item = repo.create_training_config_record(payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.InvalidReferenceError:
            return json_err("invalid_reference", 409)
        return json_ok(item=item)

    @bp.get("/training-configs/<config_id>")
    def get_training_config(config_id: str):
        item = repo.get_training_config_payload(config_id)
        if item is None:
            return json_err("not_found", 404)
        sid = item.get("subjectId")
        if sid:
            ok = _check_ownership(sid)
            if ok is False:
                return json_err("permission_denied", 403)
        return json_ok(item=item)

    @bp.put("/training-configs/<config_id>")
    def update_training_config(config_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        item = repo.get_training_config_payload(config_id)
        if item is None:
            return json_err("not_found", 404)
        sid = item.get("subjectId")
        if sid:
            ok = _check_ownership(sid)
            if ok is False:
                return json_err("permission_denied", 403)
        try:
            item = repo.update_training_config_record(config_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.InvalidReferenceError:
            return json_err("invalid_reference", 409)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.delete("/training-configs/<config_id>")
    def delete_training_config(config_id: str):
        item = repo.get_training_config_payload(config_id)
        if item is None:
            return json_err("not_found", 404)
        sid = item.get("subjectId")
        if sid:
            ok = _check_ownership(sid)
            if ok is False:
                return json_err("permission_denied", 403)
        try:
            deleted = repo.delete_training_config_record(config_id)
        except repo.ReferenceConflictError:
            return json_err("in_use", 409)
        if not deleted:
            return json_err("not_found", 404)
        return json_ok()

    @bp.get("/training-videos")
    def list_training_videos():
        page = parse_pagination(request.args, default_limit=30)
        sid = (request.args.get("subjectId") or request.args.get("subject_id") or "").strip() or None
        sort_by = (request.args.get("sortBy") or "").strip() or None
        sort_order = (request.args.get("sortOrder") or "asc").strip()
        items, total = repo.list_training_videos_page(
            keyword=page.keyword,
            subject_id=sid,
            subject_ids=_account_subject_ids(),
            training_config_id=(
                request.args.get("trainingConfigId") or request.args.get("training_config_id") or ""
            ).strip() or None,
            status=(request.args.get("status") or "").strip() or None,
            limit=page.limit,
            offset=page.offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        base = repo.TrainingVideo.query
        if page.keyword:
            pattern = f"%{page.keyword.strip()}%"
            base = base.filter(or_(
                repo.TrainingVideo.id.like(pattern),
                repo.TrainingVideo.left_original_name.like(pattern),
                repo.TrainingVideo.right_original_name.like(pattern),
                repo.TrainingVideo.status.like(pattern),
            ))
        filters_data = repo.build_filter_aggregation(
            base, repo.TrainingVideo, "training-videos",
            {"subjectId": sid},
        )

        return list_response(items, total=total, limit=page.limit, offset=page.offset,
                            extra={"filters": filters_data})

    @bp.post("/training-videos")
    def create_training_video():
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        sid = payload.get("subjectId") or payload.get("subject_id")
        if sid:
            ok = _check_ownership(sid)
            if ok is None:
                return json_err("subject_not_found", 404)
            if not ok:
                return json_err("permission_denied", 403)
        try:
            item = repo.create_training_video_metadata_record(payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.InvalidReferenceError:
            return json_err("invalid_reference", 409)
        return json_ok(item=item)

    @bp.get("/training-videos/<video_id>")
    def get_training_video(video_id: str):
        item = repo.get_training_video_payload(video_id)
        if item is None:
            return json_err("not_found", 404)
        sid = item.get("subjectId")
        if sid:
            ok = _check_ownership(sid)
            if ok is False:
                return json_err("permission_denied", 403)
        return json_ok(item=item)

    @bp.put("/training-videos/<video_id>")
    def update_training_video(video_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        item = repo.get_training_video_payload(video_id)
        if item is None:
            return json_err("not_found", 404)
        sid = item.get("subjectId")
        if sid:
            ok = _check_ownership(sid)
            if ok is False:
                return json_err("permission_denied", 403)
        try:
            item = repo.update_training_video_record(video_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.InvalidReferenceError:
            return json_err("invalid_reference", 409)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.delete("/training-videos/<video_id>")
    def delete_training_video(video_id: str):
        item = repo.get_training_video_payload(video_id)
        if item is None:
            return json_err("not_found", 404)
        sid = item.get("subjectId")
        if sid:
            ok = _check_ownership(sid)
            if ok is False:
                return json_err("permission_denied", 403)
        try:
            deleted = repo.delete_training_video_record(video_id)
        except repo.ReferenceConflictError:
            return json_err("in_use", 409)
        if not deleted:
            return json_err("not_found", 404)
        return json_ok()
