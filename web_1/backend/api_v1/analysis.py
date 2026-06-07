"""Kinematics datasets API."""

from __future__ import annotations

from flask import Blueprint, request

from backend import repositories as repo
from backend.api_utils import json_err, json_ok, list_response, parse_pagination


def _int_query(name: str) -> int | None:
    raw = request.args.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def register(bp: Blueprint) -> None:
    @bp.get("/kinematics-datasets")
    def list_kinematics_datasets():
        page = parse_pagination(request.args, default_limit=30)
        items, total = repo.list_kinematics_datasets_page(
            keyword=page.keyword,
            subject_id=(request.args.get("subjectId") or request.args.get("subject_id") or "").strip() or None,
            job_id=(request.args.get("jobId") or request.args.get("job_id") or "").strip() or None,
            training_video_id=(
                request.args.get("trainingVideoId") or request.args.get("training_video_id") or ""
            ).strip()
            or None,
            limit=page.limit,
            offset=page.offset,
        )
        return list_response(items, total=total, limit=page.limit, offset=page.offset)

    @bp.get("/kinematics-datasets/<dataset_id>")
    def get_kinematics_dataset(dataset_id: str):
        item = repo.get_kinematics_dataset_payload(dataset_id)
        if item is None:
            return json_err("not_found", 404)
        return json_ok(item=item)

    @bp.get("/kinematics-datasets/<dataset_id>/metrics")
    def list_dataset_metrics(dataset_id: str):
        page = parse_pagination(request.args, default_limit=100)
        frame_index_from = _int_query("frameIndexFrom")
        if frame_index_from is None:
            frame_index_from = _int_query("minFrameIndex")
        frame_index_to = _int_query("frameIndexTo")
        if frame_index_to is None:
            frame_index_to = _int_query("maxFrameIndex")
        result = repo.list_kinematics_metrics_page(
            dataset_id,
            frame_index_from=frame_index_from,
            frame_index_to=frame_index_to,
            limit=page.limit,
            offset=page.offset,
        )
        if result is None:
            return json_err("not_found", 404)
        items, total = result
        return list_response(items, total=total, limit=page.limit, offset=page.offset)
