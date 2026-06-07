"""Evaluations API."""

from __future__ import annotations

from flask import Blueprint, request

from backend import repositories as repo
from backend.api_utils import json_err, json_ok, list_response, parse_pagination


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


def register(bp: Blueprint) -> None:
    @bp.get("/evaluations")
    def list_evaluations():
        page = parse_pagination(request.args, default_limit=30)
        items, total = repo.list_evaluations_page(
            keyword=page.keyword,
            subject_id=(request.args.get("subjectId") or request.args.get("subject_id") or "").strip() or None,
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
        return json_ok(item=item)

    @bp.put("/evaluations/<evaluation_id>")
    def update_evaluation(evaluation_id: str):
        payload = _json_payload()
        if payload is None:
            return json_err("invalid_json", 400)
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
        if not repo.delete_evaluation_record(evaluation_id):
            return json_err("not_found", 404)
        return json_ok()
