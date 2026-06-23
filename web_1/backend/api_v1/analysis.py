"""Kinematics datasets API."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, request, send_file
from sqlalchemy import or_

from backend import repositories as repo
from backend.api_utils import get_account_id_from_headers as _account_id, json_err, json_ok, list_response, parse_pagination
from backend.models import KinematicsDataset, TrainingVideo


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
    @bp.get("/kinematics-datasets")
    def list_kinematics_datasets():
        page = parse_pagination(request.args, default_limit=30)
        sid = (request.args.get("subjectId") or request.args.get("subject_id") or "").strip() or None
        sort_by = (request.args.get("sortBy") or "").strip() or None
        sort_order = (request.args.get("sortOrder") or "asc").strip()
        items, total = repo.list_kinematics_datasets_page(
            keyword=page.keyword,
            subject_id=sid,
            subject_ids=_account_subject_ids(),
            job_id=(request.args.get("jobId") or request.args.get("job_id") or "").strip() or None,
            training_video_id=(
                request.args.get("trainingVideoId") or request.args.get("training_video_id") or ""
            ).strip() or None,
            limit=page.limit,
            offset=page.offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        base = repo.KinematicsDataset.query
        if page.keyword:
            pattern = f"%{page.keyword.strip()}%"
            base = base.filter(or_(
                repo.KinematicsDataset.id.like(pattern),
                repo.KinematicsDataset.job_id.like(pattern),
            ))
        filters_data = repo.build_filter_aggregation(
            base, repo.KinematicsDataset, "kinematics-datasets",
            {"subjectId": sid},
        )

        return list_response(items, total=total, limit=page.limit, offset=page.offset,
                            extra={"filters": filters_data})

    @bp.get("/kinematics-datasets/<dataset_id>")
    def get_kinematics_dataset(dataset_id: str):
        item = repo.get_kinematics_dataset_payload(dataset_id)
        if item is None:
            return json_err("not_found", 404)
        sid = item.get("subjectId")
        if sid:
            ok = _check_ownership(sid)
            if ok is False:
                return json_err("permission_denied", 403)
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

    @bp.get("/videos/<dataset_id>/<camera>")
    def stream_video(dataset_id: str, camera: str):
        """根据 kinematics_dataset 的 training_video 播放左/右机位视频（支持拖拽进度条）。"""
        if camera not in ("left", "right"):
            return json_err("invalid_camera", 400)

        dataset = KinematicsDataset.query.filter(KinematicsDataset.id == dataset_id).first()
        if dataset is None or not dataset.training_video_id:
            return json_err("not_found", 404)

        video = TrainingVideo.query.filter(TrainingVideo.id == dataset.training_video_id).first()
        if video is None:
            return json_err("not_found", 404)

        file_path = video.left_video_path if camera == "left" else video.right_video_path
        if not file_path:
            return json_err("not_found", 404)

        path = Path(file_path)
        if not path.exists():
            return json_err("video_file_missing", 404)

        return send_file(str(path), mimetype="video/mp4", conditional=True)

    @bp.get("/kinematics-datasets/<dataset_id>/synced-video/<camera>")
    def stream_synced_video(dataset_id: str, camera: str):
        """播放同步后的对齐视频（左/右）。文件来自 KinematicsDataset.synced_left/right_path。"""
        if camera not in ("left", "right"):
            return json_err("invalid_camera", 400)

        dataset = KinematicsDataset.query.filter(KinematicsDataset.id == dataset_id).first()
        if dataset is None:
            return json_err("not_found", 404)

        file_path = dataset.synced_left_path if camera == "left" else dataset.synced_right_path
        if not file_path:
            return json_err("not_found", 404)

        path = Path(file_path)
        if not path.exists():
            return json_err("video_file_missing", 404)

        return send_file(str(path), mimetype="video/mp4", conditional=True)

    @bp.delete("/kinematics-datasets/<dataset_id>")
    def delete_kinematics_dataset(dataset_id: str):
        """删除运动学数据集及其帧指标。"""
        ok = repo.delete_kinematics_dataset(dataset_id)
        if not ok:
            return json_err("not_found", 404)
        return json_ok()
