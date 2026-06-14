"""Build web-facing analysis payload from kinematics CSV outputs."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

CHART_BUNDLE_VERSION = 1
DEFAULT_CHART_BUNDLE_MAX_POINTS = 2000

_TIMESERIES_ARRAY_KEYS = (
    "time_s",
    "com_x",
    "com_y",
    "com_z",
    "com_cell",
    "com_speed_mps",
    "com_acceleration_mps2",
    "turning_speed_deg_s",
    "left_clearance_m",
    "right_clearance_m",
    "left_knee_angle_deg",
    "right_knee_angle_deg",
    "left_ankle_angle_deg",
    "right_ankle_angle_deg",
    "left_hip_angle_deg",
    "right_hip_angle_deg",
    "left_hip_torque_nm",
    "right_hip_torque_nm",
    "left_knee_torque_nm",
    "right_knee_torque_nm",
    "left_hip_power_w",
    "right_hip_power_w",
    "left_knee_power_w",
    "right_knee_power_w",
)

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]


def sanitize_for_json(obj: Any) -> Any:
    """Recursively replace NaN/Inf and non-JSON scalars so browser JSON.parse succeeds.

    Python's json allows NaN; ECMA-404 JSON does not, so fetch().json() throws otherwise.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int) and not isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, str):
        return obj
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    if np is not None and isinstance(obj, np.generic):
        try:
            return sanitize_for_json(obj.item())
        except (ValueError, TypeError):
            return None
    return obj


def _to_num(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def _numeric_frame(df: pd.DataFrame, cols: list[str]) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    for col in cols:
        out[col] = _to_num(df, col)
    return out


def _scalar(v: Any) -> float | int | None:
    if v is None:
        return None
    if pd.isna(v):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if float(x).is_integer():
        return int(x)
    return x


def _series_list(df: pd.DataFrame, col: str) -> list[float]:
    s = _to_num(df, col).dropna()
    return [float(x) for x in s.tolist()]


def _string_list(df: pd.DataFrame, col: str) -> list[str]:
    if col not in df.columns:
        return []
    return [str(v) if pd.notna(v) else "" for v in df[col].tolist()]


def _table_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.suffix.lower() == ".xlsx":
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    records = df.to_dict(orient="records")
    return sanitize_for_json(records)


def _summary_metrics(session_summary_df: pd.DataFrame) -> dict[str, float | int]:
    if session_summary_df.empty:
        return {}
    row = session_summary_df.iloc[0].to_dict()
    out: dict[str, float | int] = {}
    for k, v in row.items():
        sv = _scalar(v)
        if sv is not None:
            out[k] = sv
    return out


def _derived_stats(frame_df: pd.DataFrame) -> dict[str, float | int]:
    if frame_df.empty:
        return {}

    num = _numeric_frame(
        frame_df,
        [
            "com_speed_mps",
            "com_acceleration_mps2",
            "turning_speed_deg_s",
            "motion_turning_speed_deg_s",
            "left_clearance_m",
            "right_clearance_m",
            "com_cell",
            "time_s",
        ],
    )
    speed = num["com_speed_mps"].dropna()
    accel = num["com_acceleration_mps2"].dropna()
    turning = num["turning_speed_deg_s"].dropna()
    if turning.empty:
        turning = num["motion_turning_speed_deg_s"].dropna()
    left_c = num["left_clearance_m"].dropna()
    right_c = num["right_clearance_m"].dropna()
    cell = num["com_cell"]
    t = num["time_s"].dropna()

    cell_change_count = 0
    if not cell.dropna().empty:
        cell_change_count = int(cell.dropna().diff().fillna(0).ne(0).sum())

    asym = (left_c - right_c).abs().dropna()

    return {
        "frame_count": int(len(frame_df)),
        "duration_s": float(t.iloc[-1] - t.iloc[0]) if len(t) >= 2 else 0.0,
        "cell_change_count": float(cell_change_count),
        "com_speed_std_mps": float(speed.std()) if not speed.empty else 0.0,
        "com_speed_p95_mps": float(speed.quantile(0.95)) if not speed.empty else 0.0,
        "com_accel_abs_mean_mps2": float(accel.abs().mean()) if not accel.empty else 0.0,
        "com_accel_abs_p95_mps2": float(accel.abs().quantile(0.95)) if not accel.empty else 0.0,
        "turning_abs_mean_deg_s": float(turning.abs().mean()) if not turning.empty else 0.0,
        "turning_abs_p95_deg_s": float(turning.abs().quantile(0.95)) if not turning.empty else 0.0,
        "clearance_asymmetry_mean_m": float(asym.mean()) if not asym.empty else 0.0,
        "clearance_asymmetry_peak_m": float(asym.max()) if not asym.empty else 0.0,
    }


def _quality_flags(session_summary_df: pd.DataFrame, frame_df: pd.DataFrame) -> dict[str, Any]:
    row = session_summary_df.iloc[0].to_dict() if not session_summary_df.empty else {}
    status = str(row.get("segmentation_status") or "").strip() or "unknown"
    reason = str(row.get("segmentation_reason") or "").strip()
    source = str(row.get("segmentation_source") or "").strip()
    confidence = str(row.get("segmentation_confidence") or "").strip() or "none"
    fallback_level = str(row.get("segmentation_fallback_level") or "").strip() or "none"

    non_home = _scalar(row.get("segmentation_non_home_cell_frames"))
    if non_home is None:
        if "com_cell" in frame_df.columns:
            non_home = int(pd.to_numeric(frame_df["com_cell"], errors="coerce").ne(5).fillna(False).sum())
        else:
            non_home = 0
    active_ratio = _scalar(row.get("segmentation_analysis_active_ratio"))
    if active_ratio is None:
        if "analysis_active" in frame_df.columns and len(frame_df) > 0:
            active_ratio = float(pd.to_numeric(frame_df["analysis_active"], errors="coerce").fillna(0).mean())
        else:
            active_ratio = 0.0
    cycle_count = _scalar(row.get("segmentation_cycle_count"))
    if cycle_count is None:
        cycle_count = _scalar(row.get("unit_count"))
    if cycle_count is None:
        cycle_count = 0
    moving_required = _scalar(row.get("segmentation_moving_required_ratio"))
    if moving_required is None:
        moving_required = 0.0

    if status == "unknown":
        status = "ok" if int(cycle_count) > 0 else "failed"
        if status == "failed" and not reason:
            reason = "legacy_no_cycle"

    height_m = _scalar(row.get("身高_m"))
    weight_kg = _scalar(row.get("体重_kg"))
    applied_body = None
    if height_m is not None or weight_kg is not None:
        applied_body = {}
        if height_m is not None:
            applied_body["height_m"] = float(height_m)
        if weight_kg is not None:
            applied_body["weight_kg"] = float(weight_kg)

    return {
        "segmentationStatus": status,
        "segmentationReason": reason,
        "segmentationSource": source,
        "nonHomeCellFrames": int(non_home),
        "analysisActiveRatio": float(active_ratio),
        "cycleCount": int(cycle_count),
        "segmentationConfidence": confidence,
        "fallbackLevel": fallback_level,
        "movingRequiredRatio": float(moving_required),
        "appliedBody": applied_body,
    }


def _kpi_assessments(
    summary_metrics: dict[str, float | int], derived_stats: dict[str, float | int]
) -> dict[str, str]:
    """计算关键指标的评估标签（优秀/良好/需改进）。"""
    all_metrics = {**summary_metrics, **derived_stats}
    
    assessments: dict[str, str] = {}
    
    def assess(value: float | int | None, thresholds: tuple[float, float], invert: bool = False) -> str:
        if value is None:
            return "unknown"
        v = float(value)
        excellent, good = thresholds
        if invert:
            if v <= excellent:
                return "优秀"
            if v <= good:
                return "良好"
            return "待提高"
        else:
            if v >= excellent:
                return "优秀"
            if v >= good:
                return "良好"
            return "待提高"
    
    speed = _scalar(all_metrics.get("mean_com_speed_mps"))
    assessments["整体效率"] = assess(speed, (2.5, 2.0))
    
    stability = _scalar(all_metrics.get("com_speed_std_mps"))
    assessments["稳定性"] = assess(stability, (0.3, 0.5), invert=True)
    
    asymmetry = _scalar(all_metrics.get("clearance_asymmetry_peak_m"))
    assessments["对称性"] = assess(asymmetry, (0.05, 0.1), invert=True)
    
    power = _scalar(all_metrics.get("peak_com_acceleration_mps2"))
    assessments["爆发力"] = assess(power, (8.0, 6.0))
    
    consistency = _scalar(all_metrics.get("cycle_time_coeff_var"))
    assessments["循环一致性"] = assess(consistency, (5.0, 10.0), invert=True)
    
    return assessments


def _cycle_indices(frame_df: pd.DataFrame, cycle_count: int) -> list[list[int]]:
    """计算每个循环的帧索引范围。"""
    if frame_df.empty or cycle_count <= 0:
        return []
    
    total_frames = len(frame_df)
    if total_frames == 0:
        return []

    # Guard: if cycle_count exceeds total_frames, cap to avoid zero-width intervals
    if cycle_count > total_frames:
        cycle_count = total_frames

    frames_per_cycle = total_frames // cycle_count
    remainder = total_frames % cycle_count
    
    indices: list[list[int]] = []
    start = 0
    
    for i in range(cycle_count):
        end = start + frames_per_cycle + (1 if i < remainder else 0) - 1
        end = min(end, total_frames - 1)
        indices.append([start, end])
        start = end + 1
    
    return indices


def _timeseries(frame_df: pd.DataFrame) -> dict[str, list[float]]:
    num = _numeric_frame(
        frame_df,
        [
            "time_s",
            "com_x",
            "com_y",
            "com_z",
            "com_cell",
            "com_speed_mps",
            "com_acceleration_mps2",
            "turning_speed_deg_s",
            "motion_turning_speed_deg_s",
            "left_clearance_m",
            "right_clearance_m",
            "left_knee_angle_deg",
            "right_knee_angle_deg",
            "left_ankle_angle_deg",
            "right_ankle_angle_deg",
            "left_hip_angle_deg",
            "right_hip_angle_deg",
            "left_hip_torque_nm",
            "right_hip_torque_nm",
            "left_knee_torque_nm",
            "right_knee_torque_nm",
            "left_hip_power_w",
            "right_hip_power_w",
            "left_knee_power_w",
            "right_knee_power_w",
        ],
    )

    turning_vals = num["turning_speed_deg_s"].dropna().astype(float).tolist()
    if not turning_vals:
        turning_vals = num["motion_turning_speed_deg_s"].dropna().astype(float).tolist()

    def as_list(col: str) -> list[float]:
        return num[col].dropna().astype(float).tolist()

    return {
        "time_s": as_list("time_s"),
        "com_x": as_list("com_x"),
        "com_y": as_list("com_y"),
        "com_z": as_list("com_z"),
        "com_cell": as_list("com_cell"),
        "com_speed_mps": as_list("com_speed_mps"),
        "com_acceleration_mps2": as_list("com_acceleration_mps2"),
        "turning_speed_deg_s": turning_vals,
        "left_clearance_m": as_list("left_clearance_m"),
        "right_clearance_m": as_list("right_clearance_m"),
        "left_knee_angle_deg": as_list("left_knee_angle_deg"),
        "right_knee_angle_deg": as_list("right_knee_angle_deg"),
        "left_ankle_angle_deg": as_list("left_ankle_angle_deg"),
        "right_ankle_angle_deg": as_list("right_ankle_angle_deg"),
        "left_hip_angle_deg": as_list("left_hip_angle_deg"),
        "right_hip_angle_deg": as_list("right_hip_angle_deg"),
        "left_hip_torque_nm": as_list("left_hip_torque_nm"),
        "right_hip_torque_nm": as_list("right_hip_torque_nm"),
        "left_knee_torque_nm": as_list("left_knee_torque_nm"),
        "right_knee_torque_nm": as_list("right_knee_torque_nm"),
        "left_hip_power_w": as_list("left_hip_power_w"),
        "right_hip_power_w": as_list("right_hip_power_w"),
        "left_knee_power_w": as_list("left_knee_power_w"),
        "right_knee_power_w": as_list("right_knee_power_w"),
        "left_support_state": _string_list(frame_df, "left_support_state"),
        "right_support_state": _string_list(frame_df, "right_support_state"),
        "support_mode": _string_list(frame_df, "support_mode"),
    }


def _timeseries_master_len(ts: dict[str, Any]) -> int:
    time_s = ts.get("time_s")
    if not isinstance(time_s, list) or not time_s:
        return 0
    n = len(time_s)
    for k in _TIMESERIES_ARRAY_KEYS:
        if k == "time_s":
            continue
        v = ts.get(k)
        if isinstance(v, list) and len(v) < n:
            n = len(v)
    return n


def _remap_cycle_indices_for_stride(
    cycle_indices: list[Any], orig_len: int, step: int, new_len: int
) -> list[list[int]]:
    if orig_len <= 0 or new_len <= 0:
        return []
    out: list[list[int]] = []
    for item in cycle_indices:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        start = max(0, min(int(item[0]), orig_len - 1))
        end = max(0, min(int(item[1]), orig_len - 1))
        if end < start:
            end = start
        ns = start // step
        ne = end // step
        ne = min(ne, new_len - 1)
        if ne < ns:
            ne = ns
        out.append([ns, ne])
    return out


def downsample_timeseries_dict(timeseries: dict[str, Any], max_points: int) -> dict[str, Any]:
    """Uniform stride downsample; remaps cycle_indices to downsampled indices."""
    raw_ci = timeseries.get("cycle_indices")
    if not isinstance(raw_ci, list):
        raw_ci = []
    n = _timeseries_master_len(timeseries)
    if n <= 0:
        return {"cycle_indices": raw_ci}

    step = max(1, math.ceil(n / max_points))
    new_len = (n + step - 1) // step
    out: dict[str, Any] = {
        "cycle_indices": _remap_cycle_indices_for_stride(raw_ci, n, step, new_len),
    }

    for k in _TIMESERIES_ARRAY_KEYS:
        v = timeseries.get(k)
        if not isinstance(v, list):
            continue
        trimmed = v[:n]
        out[k] = [trimmed[i] for i in range(0, len(trimmed), step)]
    return sanitize_for_json(out)


def build_chart_bundle_from_payload(
    payload: dict[str, Any],
    *,
    max_points: int = DEFAULT_CHART_BUNDLE_MAX_POINTS,
) -> dict[str, Any]:
    job_id = str(payload.get("jobId") or "")
    ts_full = payload.get("timeseries") or {}
    if not isinstance(ts_full, dict):
        ts_full = {}
    ts_down = downsample_timeseries_dict(ts_full, max_points)
    return sanitize_for_json(
        {
            "ok": True,
            "jobId": job_id,
            "status": "done",
            "chartBundleVersion": CHART_BUNDLE_VERSION,
            "maxPoints": max_points,
            "timeseries": ts_down,
            "summaryMetrics": payload.get("summaryMetrics") or {},
            "derivedStats": payload.get("derivedStats") or {},
            "qualityFlags": payload.get("qualityFlags") or {},
            "kpiAssessments": payload.get("kpiAssessments") or {},
            "downloads": payload.get("downloads") or {},
        }
    )


def build_chart_bundle_from_kinematics_dir(
    *,
    job_id: str,
    kinematics_dir: Path,
    max_points: int = DEFAULT_CHART_BUNDLE_MAX_POINTS,
) -> dict[str, Any] | None:
    """Rebuild chart bundle from CSVs only (no universal2 / xlsx reads)."""
    frame_csv = kinematics_dir / "frame_metrics.csv"
    session_csv = kinematics_dir / "session_summary.csv"
    if not frame_csv.exists() or not session_csv.exists():
        return None

    step_csv = kinematics_dir / "step_metrics.csv"
    unit_csv = kinematics_dir / "unit_metrics.csv"

    frame_df = pd.read_csv(frame_csv)
    session_df = pd.read_csv(session_csv)

    summary_metrics = _summary_metrics(session_df)
    derived_stats = _derived_stats(frame_df)
    quality_flags = _quality_flags(session_df, frame_df)
    timeseries_data = _timeseries(frame_df)
    cycle_count = int(quality_flags.get("cycleCount") or 0)
    timeseries_data["cycle_indices"] = _cycle_indices(frame_df, cycle_count)

    payload_min: dict[str, Any] = {
        "jobId": job_id,
        "summaryMetrics": summary_metrics,
        "derivedStats": derived_stats,
        "qualityFlags": quality_flags,
        "kpiAssessments": _kpi_assessments(summary_metrics, derived_stats),
        "timeseries": timeseries_data,
        "downloads": {
            "frame_metrics_csv": f"/api/analysis/jobs/{job_id}/artifacts/frame_metrics.csv",
            "session_summary_csv": f"/api/analysis/jobs/{job_id}/artifacts/session_summary.csv",
            "step_metrics_csv": f"/api/analysis/jobs/{job_id}/artifacts/step_metrics.csv"
            if step_csv.exists()
            else None,
            "unit_metrics_csv": f"/api/analysis/jobs/{job_id}/artifacts/unit_metrics.csv"
            if unit_csv.exists()
            else None,
        },
    }
    return build_chart_bundle_from_payload(payload_min, max_points=max_points)


def write_chart_bundle(report_dir: Path, bundle: dict[str, Any]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "chart_bundle.json"
    path.write_text(json.dumps(sanitize_for_json(bundle), ensure_ascii=False), encoding="utf-8")
    return path


def build_result_payload(*, job_id: str, kinematics_dir: Path) -> dict[str, Any]:
    frame_csv = kinematics_dir / "frame_metrics.csv"
    session_csv = kinematics_dir / "session_summary.csv"
    step_csv = kinematics_dir / "step_metrics.csv"
    unit_csv = kinematics_dir / "unit_metrics.csv"

    frame_df = pd.read_csv(frame_csv) if frame_csv.exists() else pd.DataFrame()
    session_df = pd.read_csv(session_csv) if session_csv.exists() else pd.DataFrame()

    universal2_payload = {
        "overall": _table_records(kinematics_dir / "总体参数" / "01_总体参数表.xlsx"),
        "evaluation": _table_records(kinematics_dir / "评价参数" / "02_评价参数表.xlsx"),
        "evaluationFrame": _table_records(kinematics_dir / "评价参数" / "01_逐帧评价参数表.xlsx"),
        "torqueSummary": _table_records(kinematics_dir / "评价参数" / "03_关节力矩汇总表.xlsx"),
        "symmetryDetail": _table_records(kinematics_dir / "评价参数" / "04_步伐对称性明细表.xlsx"),
        "displacementFrame": _table_records(kinematics_dir / "位移参数" / "01_逐帧位移参数表.xlsx"),
        "airborneFrame": _table_records(kinematics_dir / "腾空参数" / "01_逐帧腾空参数表.xlsx"),
        "airborneEvents": _table_records(kinematics_dir / "腾空参数" / "02_腾空事件表.xlsx"),
        "airborneSummary": _table_records(kinematics_dir / "腾空参数" / "03_腾空汇总表.xlsx"),
        "jointFrame": _table_records(kinematics_dir / "关节参数" / "01_逐帧关节参数表.xlsx"),
        "jointSummary": _table_records(kinematics_dir / "关节参数" / "02_状态关节汇总表.xlsx"),
        "stateEvents": _table_records(kinematics_dir / "速度参数" / "02_状态事件表.xlsx"),
        "speedSummary": _table_records(kinematics_dir / "速度参数" / "03_状态速度汇总表.xlsx"),
    }

    summary_metrics = _summary_metrics(session_df)
    derived_stats = _derived_stats(frame_df)
    quality_flags = _quality_flags(session_df, frame_df)
    
    timeseries_data = _timeseries(frame_df)
    cycle_count = quality_flags.get("cycleCount", 0)
    timeseries_data["cycle_indices"] = _cycle_indices(frame_df, cycle_count)

    payload: dict[str, Any] = {
        "ok": True,
        "jobId": job_id,
        "status": "done",
        "summaryMetrics": summary_metrics,
        "derivedStats": derived_stats,
        "qualityFlags": quality_flags,
        "kpiAssessments": _kpi_assessments(summary_metrics, derived_stats),
        "timeseries": timeseries_data,
        "stepMetrics": _table_records(kinematics_dir / "step_metrics.csv") if step_csv.exists() else [],
        "unitMetrics": _table_records(kinematics_dir / "unit_metrics.csv") if unit_csv.exists() else [],
        "downloads": {
            "frame_metrics_csv": f"/api/analysis/jobs/{job_id}/artifacts/frame_metrics.csv" if frame_csv.exists() else None,
            "session_summary_csv": f"/api/analysis/jobs/{job_id}/artifacts/session_summary.csv" if session_csv.exists() else None,
            "step_metrics_csv": f"/api/analysis/jobs/{job_id}/artifacts/step_metrics.csv" if step_csv.exists() else None,
            "unit_metrics_csv": f"/api/analysis/jobs/{job_id}/artifacts/unit_metrics.csv" if unit_csv.exists() else None,
        },
        "metricVersion": "universal2",
        "universal2": universal2_payload,
    }
    return sanitize_for_json(payload)
