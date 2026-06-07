"""Flask application entry for web_1（运行时必需）: static UI, REST APIs, MySQL business data.

Owns global singletons (JobStore, result store, artifact cache) and wires the analysis
pipeline via background threads. Keep route handlers thin; heavy work lives under
backend.analysis.
"""

import json
import logging
import os
import threading
import importlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, send_file
from werkzeug.utils import secure_filename

from backend import repositories as repo
from backend.api_utils import legacy_list_response, parse_pagination
from backend.api_v1 import api_v1
from backend.db import init_database
from backend.analysis.analysis_profiles import get_profile, normalize_profile_name, resolve_frame_stride
from backend.analysis.artifact_cache import ArtifactCache
from backend.analysis.calibration.matlab_stereo_converter import (
    StereoConvertError,
    convert_matlab_stereo_file,
)
from backend.analysis.jobs import JobStore
from backend.analysis.pipeline_runner import ensure_report_json, start_pipeline_thread
from backend.analysis.perf_metrics import load_video_probe
from backend.analysis.results_store import AnalysisResultStore
from backend.analysis.report_ui_builder import build_report_ui_payload
from backend.analysis.result_builder import (
    DEFAULT_CHART_BUNDLE_MAX_POINTS,
    build_chart_bundle_from_kinematics_dir,
    sanitize_for_json,
    write_chart_bundle,
)


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["API_V1_RBAC_ENABLED"] = True
app.jinja_env.auto_reload = True
init_database(app)
app.register_blueprint(api_v1)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PROFILE_LOG = os.path.join(DATA_DIR, "profiles.jsonl")
JOBS_ROOT = Path(__file__).resolve().parent / "jobs"
ARTIFACT_CACHE_ROOT = Path(__file__).resolve().parent / "artifacts" / "immutable"
JOB_STORE = JobStore(JOBS_ROOT)
RESULT_STORE = AnalysisResultStore(Path(DATA_DIR) / "analysis_results")
ARTIFACT_CACHE = ArtifactCache(ARTIFACT_CACHE_ROOT)


def _write_job_status_to_mysql(rec) -> None:
    try:
        with app.app_context():
            repo.upsert_analysis_job_from_record(rec)
    except Exception:
        logging.exception("failed to sync analysis job state to MySQL: %s", getattr(rec, "job_id", ""))


JOB_STORE.set_status_writer(_write_job_status_to_mysql)


# Safe filenames for GET artifacts
ANALYSIS_ARTIFACTS = frozenset(
    {"frame_metrics.csv", "session_summary.csv", "step_metrics.csv", "unit_metrics.csv"}
)
SYNC_VIDEO_MODES = frozenset({"copy", "reencode"})

WEB1_ROOT = Path(__file__).resolve().parent
POSE3D_ROOT = WEB1_ROOT.parent
SPA_ROOT = WEB1_ROOT / "static" / "spa"
SITE_ROOT = POSE3D_ROOT / "site"
LEGACY_HTML_FILES = frozenset({
    "home.html",
    "loading.html",
    "product.html",
    "report.html",
    "settings.html",
    "team.html",
})


def now_iso_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_name(value):
    return " ".join(str(value or "").strip().split())





def canonical_sequence(value):
    s = str(value or "").strip().upper()
    s = s.replace("，", ",")
    s = s.replace("\r", ",").replace("\n", ",")
    s = s.replace(" ", "")
    while ",," in s:
        s = s.replace(",,", ",")
    return s.strip(",")


def _parse_sync_overrides(form) -> tuple[dict[str, object], str | None]:
    mode_raw = str(form.get("sync_video_mode", "") or "").strip().lower()
    crf_raw = str(form.get("sync_crf", "") or "").strip()
    audio_raw = str(form.get("sync_max_audio_seconds", "") or "").strip()
    out: dict[str, object] = {}

    if mode_raw:
        if mode_raw not in SYNC_VIDEO_MODES:
            return {}, "invalid_sync_video_mode"
        out["video_mode"] = mode_raw
    if crf_raw:
        try:
            crf_i = int(crf_raw)
        except (TypeError, ValueError):
            return {}, "invalid_sync_crf"
        if crf_i < 16 or crf_i > 38:
            return {}, "invalid_sync_crf"
        out["crf"] = str(crf_i)
    if audio_raw:
        try:
            max_audio_seconds = float(audio_raw)
        except (TypeError, ValueError):
            return {}, "invalid_sync_max_audio_seconds"
        if max_audio_seconds < 5.0 or max_audio_seconds > 180.0:
            return {}, "invalid_sync_max_audio_seconds"
        out["max_audio_seconds"] = round(max_audio_seconds, 3)
    return out, None


def _normalize_report_mode(form) -> str:
    """Map client training_mode (eval|free|test) to reports DB values (eval|practice|test)."""
    raw = str(form.get("training_mode") or "").strip().lower()
    if raw == "free":
        return "practice"
    if raw in ("eval", "test"):
        return raw
    return "eval"


def init_db():
    repo.init_db_runtime()


def validate_runtime_baseline() -> None:
    required_modules = ["cv2", "mediapipe", "openpyxl"]
    missing_modules = []
    for mod in required_modules:
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError:
            missing_modules.append(mod)
    if missing_modules:
        raise RuntimeError(
            "Missing runtime dependencies: "
            + ", ".join(missing_modules)
            + ". Install with: .venv\\Scripts\\python.exe -m pip install -r web_1\\requirements.txt"
        )
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("FFmpeg not found in PATH. Please install FFmpeg and add it to PATH.")
    if os.environ.get("POSE3D_VALIDATE_DB", "").strip().lower() in ("1", "true", "yes"):
        from backend.runtime_checks import validate_mysql_schema

        with app.app_context():
            validate_mysql_schema()


@app.route("/")
def spa_index():
    spa_index_path = SPA_ROOT / "index.html"
    if spa_index_path.is_file():
        resp = send_file(spa_index_path)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return resp
    return jsonify({"ok": False, "error": "spa_not_built", "hint": "Run npm run build in frontend/"}), 503


@app.route("/spa/")
@app.route("/spa/<path:asset_path>")
def spa_assets(asset_path=""):
    if not asset_path:
        spa_index_path = SPA_ROOT / "index.html"
        if spa_index_path.is_file():
            return send_file(spa_index_path)
        return jsonify({"ok": False, "error": "spa_not_built"}), 503
    target = SPA_ROOT / asset_path
    if target.is_file():
        return send_from_directory(SPA_ROOT, asset_path)
    return jsonify({"ok": False, "error": "not_found"}), 404


def _inject_legacy_html_base(html_text: str) -> str:
    if '<base href="/">' in html_text or "<base href='/'>" in html_text:
        return html_text
    return html_text.replace("<head>", '<head>\n    <base href="/">', 1)


@app.route("/legacy-html/<path:filename>")
def legacy_html(filename):
    if filename not in LEGACY_HTML_FILES:
        return jsonify({"ok": False, "error": "not_found"}), 404
    html_path = SITE_ROOT / filename
    if not html_path.is_file():
        return jsonify({"ok": False, "error": "not_found"}), 404
    html_text = html_path.read_text(encoding="utf-8")
    return _inject_legacy_html_base(html_text), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/assets/<path:asset_path>")
def site_assets(asset_path):
    target = SITE_ROOT / "assets" / asset_path
    if target.is_file():
        return send_from_directory(SITE_ROOT / "assets", asset_path)
    return jsonify({"ok": False, "error": "not_found"}), 404


@app.route("/videos/<path:asset_path>")
def spa_public_videos(asset_path):
    target = SPA_ROOT / "videos" / asset_path
    if target.is_file():
        return send_from_directory(SPA_ROOT / "videos", asset_path)
    return jsonify({"ok": False, "error": "not_found"}), 404





@app.route("/api/profile", methods=["POST"])
def save_profile():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    os.makedirs(DATA_DIR, exist_ok=True)
    record = {
        "ts": now_iso_utc(),
        **payload,
    }
    with open(PROFILE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return jsonify({"ok": True})


@app.route("/api/custom-footworks", methods=["GET"])
def list_custom_footworks():
    init_db()
    page = parse_pagination(request.args, default_limit=None)
    footwork_type_id = (request.args.get("footwork_type_id") or "").strip() or None
    items, total = repo.list_custom_footworks_page(
        keyword=page.keyword,
        footwork_type_id=footwork_type_id,
        limit=page.limit,
        offset=page.offset,
    )
    return legacy_list_response(items, paginate=page, total=total)


@app.route("/api/custom-footworks", methods=["POST"])
def create_custom_footwork():
    init_db()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    name = normalize_name(payload.get("name"))
    sequence = str(payload.get("sequence") or "").strip()
    sequence_canon = canonical_sequence(sequence)
    start_cell = payload.get("startCell")
    try:
        start_cell = int(start_cell)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "invalid_start_cell"}), 400

    if not name:
        return jsonify({"ok": False, "error": "name_required"}), 400
    if not sequence_canon:
        return jsonify({"ok": False, "error": "sequence_required"}), 400
    if start_cell < 1 or start_cell > 9:
        return jsonify({"ok": False, "error": "invalid_start_cell"}), 400

    try:
        item = repo.create_custom_footwork_record(
            name=name,
            sequence=sequence,
            sequence_canon=sequence_canon,
            start_cell=start_cell,
            rhythm=payload.get("rhythm"),
            action_requirements=payload.get("actionRequirements"),
        )
    except repo.DuplicateRecordError:
        return jsonify({"ok": False, "error": "duplicate_name_and_sequence"}), 409

    return jsonify(
        {
            "ok": True,
            "item": item,
        }
    )


@app.route("/api/custom-footworks/<item_id>", methods=["DELETE"])
def delete_custom_footwork(item_id):
    init_db()
    if not repo.soft_delete_custom_footwork(item_id):
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True})


@app.route("/api/users", methods=["GET"])
def list_users():
    init_db()
    page = parse_pagination(request.args, default_limit=None)
    items, total = repo.list_subjects_page(
        keyword=page.keyword,
        is_active=page.is_active,
        limit=page.limit,
        offset=page.offset,
    )
    return legacy_list_response(items, paginate=page, total=total)


@app.route("/api/users", methods=["POST"])
def create_user():
    init_db()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    try:
        user = repo.create_subject(payload, normalize_name=normalize_name)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify(
        {
            "ok": True,
            "user": user,
        }
    )


@app.route("/api/users/<user_id>", methods=["GET"])
def get_user(user_id):
    init_db()
    user = repo.get_subject_payload(user_id)
    if user is None:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify(
        {
            "ok": True,
            "user": user,
        }
    )


@app.route("/api/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    init_db()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    try:
        updated = repo.update_subject(user_id, payload, normalize_name=normalize_name)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    if not updated:
        return jsonify({"ok": False, "error": "not_found"}), 404

    return jsonify({"ok": True, "message": "updated"})


@app.route("/api/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    init_db()
    if not repo.soft_delete_subject(user_id):
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True})


@app.route("/api/custom-footworks/<item_id>", methods=["PUT"])
def update_custom_footwork(item_id):
    init_db()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    existing = next((item for item in repo.list_custom_footworks() if item["id"] == item_id), None)
    if existing is None:
        return jsonify({"ok": False, "error": "not_found"}), 404

    name = normalize_name(payload.get("name", existing["name"]))
    sequence = str(payload.get("sequence", existing["sequence"]) or "").strip()
    sequence_canon = canonical_sequence(sequence)
    start_cell_raw = payload.get("startCell", existing["startCell"])
    try:
        start_cell = int(start_cell_raw)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "invalid_start_cell"}), 400

    if not name:
        return jsonify({"ok": False, "error": "name_required"}), 400
    if not sequence_canon:
        return jsonify({"ok": False, "error": "sequence_required"}), 400
    if start_cell < 1 or start_cell > 9:
        return jsonify({"ok": False, "error": "invalid_start_cell"}), 400

    try:
        item = repo.update_custom_footwork_record(
            item_id,
            name=name,
            sequence=sequence,
            sequence_canon=sequence_canon,
            start_cell=start_cell,
            rhythm=payload.get("rhythm", existing.get("rhythm")),
            action_requirements=payload.get("actionRequirements", existing.get("actionRequirements")),
        )
    except repo.DuplicateRecordError:
        return jsonify({"ok": False, "error": "duplicate_name_and_sequence"}), 409
    if item is None:
        return jsonify({"ok": False, "error": "not_found"}), 404

    return jsonify(
        {
            "ok": True,
            "item": item,
        }
    )


@app.route("/api/analysis/jobs", methods=["POST"])
def create_analysis_job():
    left = request.files.get("left_video")
    right = request.files.get("right_video")
    if not left or not right or getattr(left, "filename", "") in ("", None) or getattr(right, "filename", "") in ("", None):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "missing_files",
                    "message": "请同时上传左机位与右机位视频。",
                }
            ),
            400,
        )

    fps_raw = request.form.get("fps", "60")
    try:
        fps_f = float(fps_raw)
    except (TypeError, ValueError):
        fps_f = 60.0

    profile = {}
    profile_raw = request.form.get("profile_json")
    if profile_raw:
        try:
            profile = json.loads(profile_raw)
        except json.JSONDecodeError:
            return jsonify({"ok": False, "error": "invalid_profile_json"}), 400
    analysis_profile_name = normalize_profile_name(request.form.get("analysis_profile") or "fast")
    analysis_profile = get_profile(analysis_profile_name)
    sync_overrides, sync_err = _parse_sync_overrides(request.form)
    
    if sync_err:
        return jsonify({"ok": False, "error": sync_err}), 400

    raw_step_display = request.form.get("step_display_name") or ""
    if not isinstance(raw_step_display, str):
        raw_step_display = str(raw_step_display)
    step_display_name = raw_step_display.strip()[:120]
    report_mode = _normalize_report_mode(request.form)
    training_config_id = str(request.form.get("training_config_id") or "").strip() or None

    user_id = str(request.form.get("user_id") or "").strip()
    if not user_id:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "user_id_required",
                    "message": "请先登录并选择用户后再开始分析。",
                }
            ),
            400,
        )
    init_db()
    if not repo.subject_exists(user_id):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "invalid_user_id",
                    "message": "用户不存在，请重新登录。",
                }
            ),
            400,
        )

    rec = JOB_STORE.create_job(fps=fps_f, extra_meta=profile)
    job_id = rec.job_id
    JOB_STORE.ensure_layout(job_id)
    inp = JOB_STORE.input_dir(job_id)
    left_path = inp / "left_raw.mp4"
    right_path = inp / "right_raw.mp4"
    left.save(str(left_path))
    right.save(str(right_path))
    stereo_override_path = None
    stereo_file = request.files.get("stereo_params_matlab_json")
    if stereo_file and getattr(stereo_file, "filename", "") not in ("", None):
        stereo_raw_path = inp / "stereo_params.matlab.json"
        stereo_file.save(str(stereo_raw_path))
        stereo_converted_path = inp / "stereo_params.converted.json"
        try:
            convert_matlab_stereo_file(stereo_raw_path, stereo_converted_path)
        except StereoConvertError as exc:
            return jsonify({"ok": False, "error": "invalid_stereo_params_json", "message": str(exc)}), 400
        stereo_override_path = str(stereo_converted_path)
    probe = load_video_probe(left_path)
    estimated = None
    if isinstance(probe.get("duration_s"), (int, float)):
        duration_s = float(probe["duration_s"])
        source_fps = float(probe.get("fps") or fps_f or 60.0)
        stride = resolve_frame_stride(analysis_profile.pose3d, source_fps)
        stride_factor = 1.0 / max(1, stride)
        base_mult = (
            2.8 if analysis_profile.name == "fast"
            else (4.5 if analysis_profile.name == "balanced" else 6.0)
        )
        estimated = round(duration_s * base_mult * stride_factor, 1)
    probe_fps = probe.get("fps")
    job_fps = float(probe_fps) if isinstance(probe_fps, (int, float)) and probe_fps > 0 else fps_f
    try:
        training_video_id = repo.create_training_video_record(
            subject_id=user_id,
            training_config_id=training_config_id,
            left_path=left_path,
            right_path=right_path,
            left_original_name=getattr(left, "filename", None),
            right_original_name=getattr(right, "filename", None),
            stereo_params_path=stereo_override_path,
            probe=probe,
        )
    except repo.InvalidReferenceError:
        return jsonify({"ok": False, "error": "invalid_training_config_id"}), 400
    JOB_STORE.update(
        job_id,
        fps=job_fps,
        status="queued",
        message="已排队",
        meta_patch={
            "input_saved": True,
            "analysis_profile": analysis_profile.name,
            "sync_overrides": sync_overrides,
            "input_probe": probe,
            "estimated_duration_s": estimated,
            "stereo_params_override": stereo_override_path,
            "step_display_name": step_display_name,
            "report_mode": report_mode,
            "user_id": user_id,
            "training_config_id": training_config_id,
            "training_video_id": training_video_id,
        },
    )
    JOB_STORE.write_meta_file(job_id)
    
    try:
        start_pipeline_thread(job_id, JOB_STORE, RESULT_STORE, ARTIFACT_CACHE, flask_app=app)
    except RuntimeError as exc:
        JOB_STORE.update(
            job_id,
            status="failed",
            stage=None,
            progress=0.0,
            message=str(exc),
            error=str(exc),
            error_code="QUEUE_FULL",
        )
        JOB_STORE.write_meta_file(job_id)
        return jsonify({"ok": False, "error": "queue_full", "message": str(exc)}), 429
    return jsonify(
        {
            "ok": True,
            "jobId": job_id,
            "status": "queued",
            "analysisProfile": analysis_profile.name,
            "syncOverrides": sync_overrides,
            "estimatedDurationSeconds": estimated,
           
        }
    )


@app.route("/api/analysis/jobs/<job_id>/cancel", methods=["POST"])
def cancel_analysis_job(job_id):
    rec = JOB_STORE.get(job_id)
    if rec is None:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if rec.status not in ("queued", "running"):
        return jsonify(
            {
                "ok": True,
                "jobId": job_id,
                "status": rec.status,
                "alreadyTerminal": True,
            }
        )
    JOB_STORE.update(
        job_id,
        status="failed",
        stage=None,
        progress=0.0,
        message="分析已取消",
        error="用户已取消分析",
        error_code="CANCELLED",
    )
    JOB_STORE.write_meta_file(job_id)
    return jsonify({"ok": True, "jobId": job_id, "status": "failed"})


@app.route("/api/analysis/jobs/<job_id>", methods=["GET"])
def get_analysis_job(job_id):
    rec = JOB_STORE.get(job_id)
    if rec is None:
        return jsonify({"ok": False, "error": "not_found"}), 404
    meta = rec.meta if isinstance(rec.meta, dict) else {}
    compact_meta = {
        "analysis_profile": meta.get("analysis_profile"),
        "perf_metrics": meta.get("perf_metrics"),
        "cache_hit": meta.get("cache_hit"),
        "result_id": meta.get("result_id"),
        "estimated_duration_s": meta.get("estimated_duration_s"),
    }
    return jsonify(
        {
            "ok": True,
            "job_id": rec.job_id,
            "status": rec.status,
            "stage": rec.stage,
            "progress": rec.progress,
            "message": rec.message,
            "error": rec.error,
            "error_code": rec.error_code,
            "created_at": rec.created_at,
            "updated_at": rec.updated_at,
            "fps": rec.fps,
            "meta": compact_meta,
        }
    )


@app.route("/api/analysis/jobs/<job_id>/result", methods=["GET"])
def get_analysis_result(job_id):
    rec = JOB_STORE.get(job_id)
    if rec is None:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if rec.status != "done":
        return jsonify({"ok": False, "error": "not_ready", "status": rec.status}), 400
    path = ensure_report_json(job_id, JOB_STORE)
    if path is None:
        return jsonify({"ok": False, "error": "no_result"}), 500
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    meta = rec.meta if isinstance(rec.meta, dict) else {}
    cfg = payload.get("config")
    if isinstance(cfg, dict):
        cfg = dict(cfg)
    else:
        cfg = {}
    sdn = meta.get("step_display_name")
    if isinstance(sdn, str) and sdn.strip():
        cfg["stepName"] = sdn.strip()
    rm = meta.get("report_mode")
    if rm in ("eval", "practice", "test"):
        cfg["mode"] = rm
    if cfg:
        payload["config"] = cfg
    payload = sanitize_for_json(payload)
    perf_metrics = {}
    if rec.meta and isinstance(rec.meta, dict):
        perf_metrics = rec.meta.get("perf_metrics") or {}
    payload["stageTelemetry"] = {
        "job_id": job_id,
        "stage_metrics": perf_metrics.get("stage_metrics", {}),
        "kpi": perf_metrics.get("kpi", {}),
    }
    return jsonify(payload)


@app.route("/api/analysis/jobs/<job_id>/chart-bundle", methods=["GET"])
def get_analysis_chart_bundle(job_id):
    rec = JOB_STORE.get(job_id)
    if rec is None:
        return jsonify({"ok": False, "error": "not_found"}), 404

    raw_max = request.args.get("max_points", str(DEFAULT_CHART_BUNDLE_MAX_POINTS))
    try:
        max_points = int(raw_max)
    except (TypeError, ValueError):
        max_points = DEFAULT_CHART_BUNDLE_MAX_POINTS
    max_points = max(500, min(max_points, 8000))

    report_dir = JOB_STORE.report_dir(job_id)
    bundle_path = report_dir / "chart_bundle.json"

    if bundle_path.exists():
        try:
            with open(bundle_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify(sanitize_for_json(data))
        except (OSError, json.JSONDecodeError):
            pass

    kin_dir = JOB_STORE.kinematics_dir(job_id)
    rebuilt = build_chart_bundle_from_kinematics_dir(
        job_id=job_id, kinematics_dir=kin_dir, max_points=max_points
    )
    if rebuilt is None:
        return jsonify({"ok": False, "error": "artifacts_gone"}), 404

    try:
        write_chart_bundle(report_dir, rebuilt)
    except OSError:
        pass
    return jsonify(rebuilt)


@app.route("/api/analysis/jobs/<job_id>/report-ui", methods=["GET"])
def get_analysis_report_ui(job_id):
    rec = JOB_STORE.get(job_id)
    if rec is None:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if rec.status != "done":
        return jsonify({"ok": False, "error": "not_ready", "status": rec.status}), 400

    kin_dir = JOB_STORE.kinematics_dir(job_id)
    if not kin_dir.exists():
        return jsonify({"ok": False, "error": "no_kinematics"}), 404

    history_items = RESULT_STORE.list_results(limit=20)
    try:
        payload = build_report_ui_payload(
            job_id=job_id,
            kinematics_dir=kin_dir,
            history_items=history_items,
        )
    except Exception as exc:
        logging.exception("report-ui build failed for %s", job_id)
        return jsonify({"ok": False, "error": "report_ui_build_failed", "message": str(exc)}), 500
    return jsonify(payload)


@app.route("/api/analysis/report-ui/history", methods=["GET"])
def list_report_ui_history():
    limit_raw = request.args.get("limit", "20")
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 20
    items = RESULT_STORE.list_results(limit=max(1, min(limit, 100)))
    history = []
    for item in items:
        summary = item.get("summaryMetrics") or {}
        saved_at = str(item.get("savedAt") or "")
        history.append({
            "jobId": item.get("jobId"),
            "title": f"🏓 {saved_at[:10] or '未知日期'} 乒乓球步法专项检测报告",
            "date": saved_at[:10] if saved_at else "",
            "score": summary.get("score") or summary.get("mean_com_speed_mps"),
            "summary": "历史分析记录",
        })
    return jsonify({"ok": True, "items": history})


@app.route("/api/analysis/results", methods=["GET"])
def list_analysis_results():
    limit_raw = request.args.get("limit", "30")
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 30
    limit = max(1, min(limit, 200))
    return jsonify({"ok": True, "items": RESULT_STORE.list_results(limit=limit)})


@app.route("/api/analysis/results/<result_id>", methods=["GET"])
def get_analysis_result_item(result_id):
    item = RESULT_STORE.get_result(result_id)
    if item is None:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True, "item": item})


@app.route("/api/reports", methods=["GET"])
def list_reports():
    init_db()
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"ok": False, "error": "user_id_required"}), 400

    mode = request.args.get("mode")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    step_name = request.args.get("step_name")
    limit_raw = request.args.get("limit", "30")
    offset_raw = request.args.get("offset", "0")

    try:
        limit = int(limit_raw)
        offset = int(offset_raw)
    except (TypeError, ValueError):
        limit = 30
        offset = 0
    limit = max(1, min(limit, 200))

    items, total = repo.list_reports_for_subject(
        subject_id=user_id,
        mode=mode,
        start_date=start_date,
        end_date=end_date,
        step_name=step_name,
        limit=limit,
        offset=offset,
    )

    return jsonify({
        "ok": True,
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@app.route("/api/reports/<report_id>", methods=["GET"])
def get_report(report_id):
    init_db()
    report = repo.get_report_payload(report_id)
    if report is None:
        return jsonify({"ok": False, "error": "not_found"}), 404

    return jsonify({
        "ok": True,
        "report": report,
    })


@app.route("/api/reports", methods=["POST"])
def create_report():
    init_db()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid_json"}), 400

    user_id = payload.get("user_id")
    job_id = payload.get("job_id")
    mode = payload.get("mode", "eval")
    step_name = payload.get("step_name")
    summary = payload.get("summary", {})

    if not user_id or not job_id:
        return jsonify({"ok": False, "error": "user_id_and_job_id_required"}), 400

    report_id = repo.upsert_evaluation_and_report(
        subject_id=user_id,
        job_id=job_id,
        mode=mode,
        step_name=step_name,
        summary=summary,
    )
    if report_id is None:
        return jsonify({"ok": False, "error": "invalid_user_id"}), 400
    report = repo.get_report_payload(report_id) or {}

    return jsonify({
        "ok": True,
        "report": report,
    })


@app.route("/api/reports/<report_id>", methods=["DELETE"])
def delete_report(report_id):
    init_db()
    if not repo.delete_report_record(report_id):
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True})


@app.route("/api/reports/compare", methods=["GET"])
def compare_reports():
    ids_raw = request.args.get("ids")
    if not ids_raw:
        return jsonify({"ok": False, "error": "ids_required"}), 400

    report_ids = [id.strip() for id in ids_raw.split(",") if id.strip()]
    if len(report_ids) < 2:
        return jsonify({"ok": False, "error": "at_least_two_ids_required"}), 400

    init_db()
    reports_data = repo.compare_report_records(report_ids)

    return jsonify({
        "ok": True,
        "reports": reports_data,
    })


@app.route("/api/analysis/jobs/<job_id>/artifacts/<filename>", methods=["GET"])
def download_analysis_artifact(job_id, filename):
    safe = secure_filename(filename)
    if safe != filename or filename not in ANALYSIS_ARTIFACTS:
        return jsonify({"ok": False, "error": "forbidden"}), 400
    rec = JOB_STORE.get(job_id)
    if rec is None:
        return jsonify({"ok": False, "error": "not_found"}), 404
    kin = JOB_STORE.kinematics_dir(job_id)
    target = kin / filename
    if not target.is_file():
        return jsonify({"ok": False, "error": "not_found"}), 404
    return send_from_directory(kin, filename, as_attachment=True)


@app.route("/api/app/exit", methods=["POST"])
def exit_app():
    shutdown_func = request.environ.get("werkzeug.server.shutdown")
    if shutdown_func is not None:
        threading.Timer(0.2, shutdown_func).start()
        return jsonify({"ok": True, "message": "shutting_down"})
    threading.Timer(0.2, lambda: os._exit(0)).start()
    return jsonify({"ok": True, "message": "force_exit"})


# --- 专门为训练页面提供的硬件触发接口 ---
@app.route("/api/hardware/start", methods=["POST"])
def trigger_hardware_api():
    try:
        # 采用动态导入，即使硬件脚本报错也不会导致主程序崩溃
        from scripts.hardware.start_signal import run_feedback
        success = run_feedback()
        if success:
            return jsonify({"ok": True}), 200
        else:
            return jsonify({"ok": False, "error": "Hardware communication failed"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    init_db()
    validate_runtime_baseline()
    # 默认关闭 reloader：否则代码保存会重启进程，内存任务丢失并导致轮询 404。
    # 需要热重载时可设环境变量 FLASK_USE_RELOADER=1
    _use_reload = os.environ.get("FLASK_USE_RELOADER", "").strip() in ("1", "true", "yes")
    app.run(debug=True, use_reloader=_use_reload)
