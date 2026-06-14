"""Background pipeline with profiling, profiles and stage cache."""

from __future__ import annotations

import json
import os
import shutil
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import jobs
from .analysis_profiles import effective_analysis_fps, get_profile, resolve_frame_stride
from .artifact_cache import ArtifactCache
from .executor import AnalysisExecutor
from .perf_metrics import StageTimer, load_video_probe, now_iso, write_perf_snapshot
from . import sync_service
from .kinematics_service import run_kinematics
from .pose3d_service import (
    build_user_settings,
    default_stereo_params_path,
    prepare_batch_job_videos,
    run_pose3d_pipeline_simple,
    write_user_params_py,
)
from .report_persistence import upsert_report_for_job
from .result_builder import build_chart_bundle_from_payload, build_result_payload, write_chart_bundle
from .results_store import AnalysisResultStore
from .data_validator import write_quality_report
from ..repositories import upsert_kinematics_dataset_for_job

_EXECUTOR = AnalysisExecutor()

_TRUE_SET = {"1", "true", "yes", "on"}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in _TRUE_SET


def _choose_primary_pose3d_csv(collect_dir: Path) -> Path:
    candidates = [
        collect_dir / "pose3d_wide_processed.csv",
        collect_dir / "pose3d_abs_zup_ground0.csv",
        collect_dir / "pose3d_abs_filtered_zup_ground0.csv",
        collect_dir / "pose3d_abs_filtered.csv",
        collect_dir / "pose3d_abs.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"未找到可用的 3D CSV，候选: {[str(p) for p in candidates]}"
    )


def _restore_optional_ground0(cache: ArtifactCache, key: str, collect_dir: Path) -> bool:
    restored = False
    for name in ("pose3d_abs_zup_ground0.csv", "pose3d_wide.csv", "pose3d_wide_processed.csv"):
        src = cache._stage_dir("pose3d", key) / name
        if not src.exists():
            continue
        dst = collect_dir / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        restored = True
    return restored


def _save_optional_ground0(cache: ArtifactCache, key: str, collect_dir: Path) -> bool:
    saved = False
    dst_dir = cache._stage_dir("pose3d", key)
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in ("pose3d_abs_zup_ground0.csv", "pose3d_wide.csv", "pose3d_wide_processed.csv"):
        src = collect_dir / name
        if not src.exists():
            continue
        shutil.copy2(src, dst_dir / name)
        saved = True
    return saved


def _fail(store: jobs.JobStore, job_id: str, code: str, msg: str, root: Path) -> None:
    jobs.append_log(root, f"FAILED [{code}] {msg}")
    store.update(job_id, status="failed", error=msg, error_code=code, message=msg)
    store.write_meta_file(job_id)


def _record_mysql_persistence_warning(
    store: jobs.JobStore,
    job_id: str,
    log: Callable[[str], None],
    *,
    target: str,
    error_code: str,
    message: str,
) -> None:
    log(f"Warning [{error_code}] {target}: {message}")
    rec = store.get(job_id)
    existing_errors: list[dict[str, Any]] = []
    existing_codes: list[str] = []
    if rec and isinstance(rec.meta, dict):
        raw_errors = rec.meta.get("mysql_persistence_errors")
        if isinstance(raw_errors, list):
            existing_errors = [dict(item) for item in raw_errors if isinstance(item, dict)]
        raw_codes = rec.meta.get("persistence_warning_codes")
        if isinstance(raw_codes, list):
            existing_codes = [str(code) for code in raw_codes if str(code).strip()]
    existing_errors.append(
        {
            "target": target,
            "error_code": error_code,
            "message": message,
        }
    )
    if error_code not in existing_codes:
        existing_codes.append(error_code)
    store.update(
        job_id,
        meta_patch={
            "mysql_persistence_status": "partial_failure",
            "mysql_persistence_errors": existing_errors,
            "persistence_warning_codes": existing_codes,
        },
    )


def _upsert_report_for_job_observable(
    *,
    store: jobs.JobStore,
    log: Callable[[str], None],
    user_id: str,
    job_id: str,
    mode: str,
    step_name: str | None,
    payload: dict[str, Any],
) -> str | None:
    try:
        report_id = upsert_report_for_job(
            user_id=user_id,
            job_id=job_id,
            mode=mode,
            step_name=step_name,
            payload=payload,
        )
    except Exception as exc:
        _record_mysql_persistence_warning(
            store,
            job_id,
            log,
            target="evaluation_report",
            error_code="MYSQL_REPORT_WRITE_FAILED",
            message=f"{type(exc).__name__}: {exc}",
        )
        return None
    if not report_id:
        _record_mysql_persistence_warning(
            store,
            job_id,
            log,
            target="evaluation_report",
            error_code="MYSQL_REPORT_WRITE_FAILED",
            message=f"report upsert returned empty id for user={user_id}",
        )
    return report_id


def _unlink_if_exists(path: Path, log: Callable[[str], None]) -> None:
    try:
        if path.is_file():
            path.unlink()
            log(f"清理产物: {path}")
    except OSError as exc:
        log(f"清理失败: {path} ({exc})")


def _cleanup_job_artifacts(store: jobs.JobStore, job_id: str, log: Callable[[str], None]) -> None:
    keep_input = _env_flag("ANALYSIS_KEEP_INPUT_VIDEOS", default=True)
    keep_synced = _env_flag("ANALYSIS_KEEP_SYNC_VIDEOS", default=False)
    keep_intermediates = _env_flag("ANALYSIS_KEEP_INTERMEDIATES", default=False)

    if not keep_input:
        inp = store.input_dir(job_id)
        _unlink_if_exists(inp / "left_raw.mp4", log)
        _unlink_if_exists(inp / "right_raw.mp4", log)

    if not keep_synced:
        synced = store.synced_dir(job_id)
        _unlink_if_exists(synced / "left_aligned.mp4", log)
        _unlink_if_exists(synced / "right_aligned.mp4", log)

    if keep_intermediates:
        return

    pose3d_out = store.pose3d_out_dir(job_id)
    for rel in (
        ("pair_001", "pose2d_all.csv"),
        ("pair_001", "pose3d_abs.csv"),
        ("pair_001", "pose3d_relative.csv"),
        ("pair_001", "pose3d_abs_filtered.csv"),
        ("pair_001", "pose3d_abs_filtered_zup_ground0.csv"),
        ("pair_001", "pose3d_relative_filtered.csv"),
    ):
        _unlink_if_exists(pose3d_out.joinpath(*rel), log)

    _unlink_if_exists(store.job_dir(job_id) / "pose3d_user_params.py", log)


class PipelineStep:
    name: str

    def run(self) -> Any:
        raise NotImplementedError()


@dataclass
class CallableStep(PipelineStep):
    name: str
    fn: Callable[[], Any]

    def run(self) -> Any:
        return self.fn()


def _stage_meta_payload(
    *,
    stage_timer: StageTimer,
    profile_name: str,
    input_probe: dict[str, object],
    cache_hits: dict[str, bool],
    effective_params: dict[str, object],
    pose3d_substage_metrics: dict[str, object] | None = None,
) -> dict[str, object]:
    total_s = 0.0
    stages = stage_timer.as_dict()
    for row in stages.values():
        if isinstance(row.get("duration_s"), (int, float)):
            total_s += float(row["duration_s"])
    t_sync = float(stages.get("sync", {}).get("duration_s", 0.0) or 0.0)
    t_pose3d = float(stages.get("pose3d", {}).get("duration_s", 0.0) or 0.0)
    t_kinematics = float(stages.get("kinematics", {}).get("duration_s", 0.0) or 0.0)
    sub = dict(pose3d_substage_metrics or {})
    t_pose2d = float(sub.get("pose2d_s", 0.0) or 0.0)
    t_triangulate = float(sub.get("triangulate_s", 0.0) or 0.0)
    t_filter = float(sub.get("temporal_filter_s", 0.0) or 0.0)
    input_seconds = input_probe.get("duration_s")
    realtime = None
    if isinstance(input_seconds, (int, float)) and total_s > 0:
        realtime = round(float(input_seconds) / total_s, 3)
    return {
        "generated_at": now_iso(),
        "profile": profile_name,
        "input_video": input_probe,
        "effective_params": effective_params,
        "stage_metrics": stages,
        "pose3d_substage_metrics": sub,
        "cache_hit": cache_hits,
        "kpi": {
            "T_sync": round(t_sync, 3),
            "T_pose2d": round(t_pose2d, 3),
            "T_triangulate": round(t_triangulate, 3),
            "T_filter": round(t_filter, 3),
            "T_pose3d": round(t_pose3d, 3),
            "T_kinematics": round(t_kinematics, 3),
            "T_total": round(total_s, 3),
            "realtime_ratio": realtime,
        },
    }


def run_job_pipeline(
    job_id: str,
    store: jobs.JobStore,
    result_store: AnalysisResultStore | None = None,
    cache: ArtifactCache | None = None,
) -> None:
    root = store.job_dir(job_id)
    store.ensure_layout(job_id)

    def log(line: str) -> None:
        jobs.append_log(root, line)

    stage_timer = StageTimer()
    cache_hits: dict[str, bool] = {"sync": False, "pose3d": False}

    try:
        inp = store.input_dir(job_id)
        left_raw = inp / "left_raw.mp4"
        right_raw = inp / "right_raw.mp4"
        if not left_raw.exists() or not right_raw.exists():
            _fail(store, job_id, "UPLOAD_MISSING", "需要同时上传左、右机位视频。", root)
            return
        rec = store.get(job_id)
        profile_name = str((rec.meta if rec else {}).get("analysis_profile") or "快速")
        profile = get_profile(profile_name)
        sync_overrides = dict((rec.meta if rec else {}).get("sync_overrides") or {})

        def _override(key, default):
            val = sync_overrides.get(key)
            return val if val is not None else default

        sync_video_mode = str(_override("video_mode", profile.sync.video_mode))
        sync_crf = str(_override("crf", profile.sync.crf))
        sync_max_audio_seconds = float(_override("max_audio_seconds", profile.sync.max_audio_seconds))
        input_probe = load_video_probe(left_raw)
        source_fps = float(input_probe.get("fps") or (rec.fps if rec else 60.0))
        frame_stride = resolve_frame_stride(profile.pose3d, source_fps)
        eff_fps = effective_analysis_fps(source_fps, frame_stride)
        effective_params = {
            "sync": {
                "video_mode": sync_video_mode,
                "crf": sync_crf,
                "max_audio_seconds": sync_max_audio_seconds,
            },
            "pose3d": {
                "max_frames": profile.pose3d.max_frames,
                "frame_stride": frame_stride,
                "target_analysis_fps": profile.pose3d.target_analysis_fps,
                "effective_analysis_fps": eff_fps,
                "temporal_filter_enabled": profile.pose3d.temporal_filter_enabled,
                "temporal_filter_window_size": profile.pose3d.temporal_filter_window_size,
            },
        }
        store.update(
            job_id,
            fps=source_fps if source_fps > 0 else None,
            meta_patch={
                "analysis_profile": profile.name,
                "effective_params": effective_params,
                "input_probe": input_probe,
            },
        )

        store.update(
            job_id,
            status="running",
            stage="sync",
            progress=0.05,
            message="双机位同步中…",
        )
        store.write_meta_file(job_id)

        synced = store.synced_dir(job_id)
        out_l = synced / "left_aligned.mp4"
        out_r = synced / "right_aligned.mp4"

        class SyncProgress:
            def set_phase(self, desc: str) -> None:
                store.update(job_id, message=str(desc))

            def set_overall(self, value: float) -> None:
                v = max(0.0, min(1.0, float(value)))
                store.update(job_id, progress=0.05 + 0.20 * v)

        stage_timer.start("sync")
        sync_key = None
        if cache is not None:
            sync_key = cache.build_stage_key(
                "sync",
                file_paths=[left_raw, right_raw],
                file_roles=["left_raw", "right_raw"],
                params={
                    "video_mode": sync_video_mode,
                    "crf": sync_crf,
                    "max_audio_seconds": sync_max_audio_seconds,
                },
            )
            cache_hits["sync"] = cache.restore(
                "sync",
                sync_key,
                outputs={"left_aligned.mp4": out_l, "right_aligned.mp4": out_r},
            )
        if cache_hits["sync"]:
            log("同步阶段缓存命中，复用对齐视频。")
        else:
            sync_step = CallableStep(
                name="sync",
                fn=lambda: sync_service.run_job_sync(
                    left_in=left_raw,
                    right_in=right_raw,
                    left_out=out_l,
                    right_out=out_r,
                    log_fn=log,
                    progress_sink=SyncProgress(),
                    video_mode=sync_video_mode,
                    crf=sync_crf,
                    max_audio_seconds=sync_max_audio_seconds,
                ),
            )
            sync_result = dict(sync_step.run() or {})
            if sync_result:
                effective_params["sync"].update(sync_result)
                store.update(job_id, meta_patch={"effective_params": effective_params})
            if cache is not None and sync_key is not None:
                cache.save(
                    "sync",
                    sync_key,
                    outputs={"left_aligned.mp4": out_l, "right_aligned.mp4": out_r},
                )
        stage_timer.end("sync", cache_hit=cache_hits["sync"])

        store.update(job_id, stage="pose3d", progress=0.30, message="三维姿态重建…")
        store.write_meta_file(job_id)
        pose3d_substage_metrics: dict[str, object] = {}

        data_root = store.pose3d_session_dir(job_id)
        pose_out = store.pose3d_out_dir(job_id)
        collect = store.pose3d_collect_dir(job_id)
        stereo = default_stereo_params_path()
        rec_for_stereo = store.get(job_id)
        if rec_for_stereo:
            override = rec_for_stereo.meta.get("stereo_params_override")
            if override:
                stereo = Path(str(override))
                log(f"使用任务内标定参数: {stereo}")
        pair_info = prepare_batch_job_videos(
            job_id=job_id,
            synced_left=out_l,
            synced_right=out_r,
            data_root=data_root,
            stereo_src=stereo,
            log_fn=log,
        )
        user_settings = build_user_settings(
            data_root=data_root,
            output_root=pose_out,
            groups=[pair_info["group"]],
            detector_max_frames=profile.pose3d.max_frames,
            frame_stride=frame_stride,
            temporal_filter_enabled=profile.pose3d.temporal_filter_enabled,
            temporal_filter_window_size=profile.pose3d.temporal_filter_window_size,
        )
        user_settings["_web_pair_info"] = pair_info
        log(
            f"pose3d 采样: source_fps={source_fps:.1f}, frame_stride={frame_stride}, "
            f"effective_fps={eff_fps}"
        )

        class Pose3dProgress:
            def __call__(self, ratio: float, message: str) -> None:
                v = max(0.0, min(1.0, float(ratio)))
                store.update(
                    job_id,
                    progress=0.30 + 0.40 * v,
                    message=str(message),
                )

        pose3d_progress = Pose3dProgress()
        user_params = root / "pose3d_user_params.py"
        if os.environ.get("POSE3D_DUMP_USER_PARAMS", "").strip().lower() in ("1", "true", "yes"):
            write_user_params_py(
                dest_py=user_params,
                data_root=data_root,
                output_root=pose_out,
                groups=[pair_info["group"]],
                log_fn=log,
                detector_max_frames=profile.pose3d.max_frames,
                frame_stride=frame_stride,
                temporal_filter_enabled=profile.pose3d.temporal_filter_enabled,
                temporal_filter_window_size=profile.pose3d.temporal_filter_window_size,
            )
        stage_timer.start("pose3d")
        pose_key = None
        primary_csv = collect / "pose3d_wide_processed.csv"
        if cache is not None:
            pose3d_cache_params = {
                "pipeline": "pose3d_batch_v3",
                "reconstruction_mode": str(user_settings.get("pose3d", {}).get("reconstruction_mode")),
                "max_frames": profile.pose3d.max_frames,
                "frame_stride": frame_stride,
                "target_analysis_fps": profile.pose3d.target_analysis_fps,
                "postprocess_enabled": profile.pose3d.temporal_filter_enabled,
                "postprocess_window_size": profile.pose3d.temporal_filter_window_size,
            }
            log("pose3d缓存参数: " + json.dumps(pose3d_cache_params, ensure_ascii=False))
            pose_key = cache.build_stage_key(
                "pose3d",
                file_paths=[out_l, out_r, data_root / pair_info["group"] / "stereo_params.json"],
                file_roles=["left_aligned", "right_aligned", "stereo_params"],
                params=pose3d_cache_params,
            )
            cache_hits["pose3d"] = cache.restore(
                "pose3d",
                pose_key,
                outputs={
                    "pose3d_abs.csv": collect / "pose3d_abs.csv",
                    "pose3d_abs_zup_ground0.csv": collect / "pose3d_abs_zup_ground0.csv",
                    "pose3d_wide_processed.csv": collect / "pose3d_wide_processed.csv",
                },
            )
            if cache_hits["pose3d"]:
                _restore_optional_ground0(cache, pose_key, collect)
        if cache_hits["pose3d"]:
            primary_csv = _choose_primary_pose3d_csv(collect)
            log("pose3d 阶段缓存命中，复用三维结果。")
        else:
            pose_step = CallableStep(
                name="pose3d",
                fn=lambda: run_pose3d_pipeline_simple(
                    user_params_path=user_params if user_params.exists() else None,
                    settings=user_settings,
                    pair_out_dir=pose_out,
                    collect_dir=collect,
                    log_fn=log,
                    progress_callback=pose3d_progress,
                ),
            )
            primary_csv, _, pose3d_substage_metrics = pose_step.run()
            if cache is not None and pose_key is not None:
                cache.save(
                    "pose3d",
                    pose_key,
                    outputs={
                        "pose3d_abs.csv": collect / "pose3d_abs.csv",
                        "pose3d_abs_zup_ground0.csv": collect / "pose3d_abs_zup_ground0.csv",
                        "pose3d_wide_processed.csv": collect / "pose3d_wide_processed.csv",
                    },
                )
                _save_optional_ground0(cache, pose_key, collect)
            primary_csv = _choose_primary_pose3d_csv(collect)
        stage_timer.end("pose3d", cache_hit=cache_hits["pose3d"], substage_metrics=pose3d_substage_metrics)

        rec_after_pose = store.get(job_id)
        probe_fps = None
        if rec_after_pose and isinstance(rec_after_pose.meta.get("input_probe"), dict):
            raw_fps = rec_after_pose.meta["input_probe"].get("fps")
            if isinstance(raw_fps, (int, float)) and raw_fps > 0:
                probe_fps = float(raw_fps)
        fps = (
            float(eff_fps)
            if isinstance(eff_fps, (int, float)) and eff_fps > 0
            else (probe_fps if probe_fps is not None else (float(rec_after_pose.fps) if rec_after_pose else 60.0))
        )

        store.update(job_id, stage="kinematics", progress=0.72, message="运动学分析…")
        store.write_meta_file(job_id)

        kin_dir = store.kinematics_dir(job_id)
        profile_payload = (
            (rec_after_pose.meta.get("profile") if rec_after_pose and isinstance(rec_after_pose.meta, dict) else {}) or {}
        )
        log(
            "kinematics输入: "
            + json.dumps(
                {
                    "pose3d_csv": str(primary_csv),
                    "fps": fps,
                    "profile_keys": sorted(list(profile_payload.keys())),
                },
                ensure_ascii=False,
            )
        )
        stage_timer.start("kinematics")
        kin_step = CallableStep(
            name="kinematics",
            fn=lambda: run_kinematics(
                pose3d_csv=primary_csv,
                output_dir=kin_dir,
                fps=fps,
                log_fn=log,
                profile=profile_payload,
            ),
        )
        kin_step.run()
        stage_timer.end("kinematics", cache_hit=False)

        stage_timer.start("result")
        payload = build_result_payload(job_id=job_id, kinematics_dir=kin_dir)
        report_path = store.report_dir(job_id) / "report_payload.json"
        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        bundle = build_chart_bundle_from_payload(payload)
        chart_bundle_path = write_chart_bundle(store.report_dir(job_id), bundle)
        # Write data quality report for frontend diagnostics
        quality_path = write_quality_report(kin_dir, store.report_dir(job_id))
        log(f"数据质量报告: {quality_path}")
        rec_done = store.get(job_id)
        if result_store is not None:
            result_id = result_store.save_result(
                job_id=job_id,
                payload=payload,
                job_meta=dict(rec_done.meta) if rec_done else {},
                report_path=report_path,
            )
            store.update(job_id, meta_patch={"result_id": result_id})
        stage_timer.end("result", cache_hit=False)

        rec_done = store.get(job_id)
        if rec_done and isinstance(rec_done.meta, dict):
            bound_user_id = str(rec_done.meta.get("user_id") or "").strip()
            training_video_id = str(rec_done.meta.get("training_video_id") or "").strip() or None
            try:
                dataset_id = upsert_kinematics_dataset_for_job(
                    job_id=job_id,
                    subject_id=bound_user_id or None,
                    training_video_id=training_video_id,
                    report_path=report_path,
                    chart_bundle_path=chart_bundle_path,
                    kinematics_dir=kin_dir,
                    payload=payload,
                    synced_left_path=out_l,
                    synced_right_path=out_r,
                )
                store.update(job_id, meta_patch={"kinematics_dataset_id": dataset_id})
            except Exception as exc:
                _record_mysql_persistence_warning(
                    store,
                    job_id,
                    log,
                    target="kinematics_dataset",
                    error_code="MYSQL_KINEMATICS_DATASET_WRITE_FAILED",
                    message=f"{type(exc).__name__}: {exc}",
                )
            if bound_user_id:
                try:
                    report_id = _upsert_report_for_job_observable(
                        store=store,
                        log=log,
                        user_id=bound_user_id,
                        job_id=job_id,
                        mode=str(rec_done.meta.get("report_mode") or "eval"),
                        step_name=str(rec_done.meta.get("step_display_name") or "视频分析"),
                        payload=payload,
                    )
                    if report_id:
                        log(f"已写入历史报告: {report_id} (user={bound_user_id})")
                    else:
                        log(f"警告: 未能写入历史报告，用户不存在: {bound_user_id}")
                except Exception as exc:
                    log(f"警告: 写入历史报告失败: {type(exc).__name__}: {exc}")
            else:
                log("警告: 任务未绑定 user_id，跳过写入历史报告。")

        perf_payload = _stage_meta_payload(
            stage_timer=stage_timer,
            profile_name=profile.name,
            input_probe=input_probe,
            cache_hits=cache_hits,
            effective_params=effective_params,
            pose3d_substage_metrics=pose3d_substage_metrics,
        )
        perf_path = write_perf_snapshot(store.report_dir(job_id), perf_payload)
        store.update(
            job_id,
            meta_patch={
                "cache_hit": cache_hits,
                "perf_metrics": perf_payload,
                "perf_metrics_path": str(perf_path),
            },
        )

        store.update(
            job_id,
            status="done",
            stage=None,
            progress=1.0,
            message="分析完成",
            error=None,
            error_code=None,
        )
    except Exception as e:
        tb = traceback.format_exc()
        log(tb)
        stage = store.get(job_id)
        st = stage.stage if stage else None
        code = "PIPELINE_FAILED"
        if st == "sync":
            code = "SYNC_FAILED"
        elif st == "pose3d":
            code = "POSE3D_FAILED"
        elif st == "kinematics":
            code = "KINEMATICS_FAILED"
        _fail(store, job_id, code, f"{type(e).__name__}: {e}", root)
    else:
        # 仅分析成功时执行清理和元数据写入，异常不会覆盖 done 状态
        _cleanup_job_artifacts(store, job_id, log)
        store.write_meta_file(job_id)
        log("Pipeline 完成。")


def start_pipeline_thread(
    job_id: str,
    store: jobs.JobStore,
    result_store: AnalysisResultStore | None = None,
    cache: ArtifactCache | None = None,
    flask_app: object | None = None,
) -> None:
    def _task() -> None:
        if flask_app is not None:
            with flask_app.app_context():
                run_job_pipeline(job_id, store, result_store, cache)
            return
        run_job_pipeline(job_id, store, result_store, cache)

    _EXECUTOR.submit(_task)


def ensure_report_json(job_id: str, store: jobs.JobStore) -> Path | None:
    """Ensure report exists and is refreshed only when upstream CSV changed."""
    kin = store.kinematics_dir(job_id)
    report = store.report_dir(job_id) / "report_payload.json"
    session_csv = kin / "session_summary.csv"
    if not session_csv.exists():
        return None
    needs_refresh = not report.exists()
    if not needs_refresh:
        latest_src_mtime = max(
            p.stat().st_mtime
            for p in [
                kin / "frame_metrics.csv",
                kin / "step_metrics.csv",
                kin / "unit_metrics.csv",
                session_csv,
            ]
            if p.exists()
        )
        needs_refresh = latest_src_mtime > report.stat().st_mtime
    if needs_refresh:
        payload = build_result_payload(job_id=job_id, kinematics_dir=kin)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        bundle = build_chart_bundle_from_payload(payload)
        write_chart_bundle(report.parent, bundle)
        write_quality_report(kin, report.parent)
    return report
