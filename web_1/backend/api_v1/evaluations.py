"""Evaluations API."""

from __future__ import annotations

from flask import Blueprint, request

from backend import repositories as repo
from backend.api_utils import get_account_id_from_headers as _account_id, json_err, json_ok, list_response, parse_pagination


def _json_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None
    return payload


def _int_query(name: str) -> int | None:
    raw = request.args.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _account_subject_ids() -> list[str] | None:
    aid = _account_id()
    if not aid:
        return None
    return repo._subject_ids_for_account(aid)  # 空列表→无数据


def _check_ownership(subject_id: str) -> bool | None:
    aid = _account_id()
    if not aid:
        return True
    return repo.check_subject_ownership(subject_id, aid)


def register(bp: Blueprint) -> None:
    @bp.get("/evaluations")
    def list_evaluations():
        page = parse_pagination(request.args, default_limit=30)
        items, total = repo.list_evaluations_page(
            keyword=page.keyword,
            subject_id=(request.args.get("subjectId") or request.args.get("subject_id") or "").strip() or None,
            subject_ids=_account_subject_ids(),
            analysis_job_id=(request.args.get("analysisJobId") or request.args.get("analysis_job_id") or "").strip()
            or None,
            kinematics_dataset_id=(
                request.args.get("kinematicsDatasetId") or request.args.get("kinematics_dataset_id") or ""
            ).strip()
            or None,
            footwork_type_id=(request.args.get("footworkTypeId") or request.args.get("footwork_type_id") or "").strip()
            or None,
            route_definition_id=(
                request.args.get("routeDefinitionId") or request.args.get("route_definition_id") or ""
            ).strip()
            or None,
            grade=(request.args.get("grade") or "").strip() or None,
            min_score=_int_query("minScore"),
            max_score=_int_query("maxScore"),
            limit=page.limit,
            offset=page.offset,
        )
        return list_response(items, total=total, limit=page.limit, offset=page.offset)

    @bp.post("/evaluations")
    def create_evaluation():
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
            item = repo.create_evaluation_record(payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.InvalidReferenceError:
            return json_err("invalid_reference", 409)
        return json_ok(item=item)

    @bp.get("/evaluations/<evaluation_id>")
    def get_evaluation(evaluation_id: str):
        item = repo.get_evaluation_payload(evaluation_id)
        if item is None:
            return json_err("not_found", 404)
        sid = item.get("subjectId")
        if sid:
            ok = _check_ownership(sid)
            if ok is False:
                return json_err("permission_denied", 403)
        return json_ok(item=item)

    @bp.put("/evaluations/<evaluation_id>")
    def update_evaluation(evaluation_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
        item = repo.get_evaluation_payload(evaluation_id)
        if item is None:
            return json_err("not_found", 404)
        sid = item.get("subjectId")
        if sid:
            ok = _check_ownership(sid)
            if ok is False:
                return json_err("permission_denied", 403)
        try:
            item = repo.update_evaluation_record(evaluation_id, payload)
        except ValueError as exc:
            return json_err(str(exc), 400)
        except repo.InvalidReferenceError:
            return json_err("invalid_reference", 409)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.delete("/evaluations/<evaluation_id>")
    def delete_evaluation(evaluation_id: str):
        item = repo.get_evaluation_payload(evaluation_id)
        if item is None:
            return json_err("not_found", 404)
        sid = item.get("subjectId")
        if sid:
            ok = _check_ownership(sid)
            if ok is False:
                return json_err("permission_denied", 403)
        if not repo.delete_evaluation_record(evaluation_id):
            return json_err("not_found", 404)
        return json_ok()
