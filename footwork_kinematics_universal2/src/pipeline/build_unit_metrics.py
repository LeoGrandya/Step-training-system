from __future__ import annotations

import math
from typing import Optional

import pandas as pd

from src.metrics.unit.unit_metrics_stub import UNIT_COLUMNS


# ============================================================
# 【阈值可改】事件最短连续帧数
# ------------------------------------------------------------
# 若某类腾空事件连续帧数 < EVENT_MIN_FRAMES，则该事件不计次数。
# 时间统计依然按实际帧数累计；这里只影响“次数”。
# ============================================================
EVENT_MIN_FRAMES = 1


# ============================================================
# 【阈值可改】方向分量判定阈值（单位：米）
# ------------------------------------------------------------
# 用于判断一次 move / restore 是左右、前后，还是斜向。
# ============================================================
DIRECTION_COMPONENT_THRESHOLD_M = 0.05


def _safe_series(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce").dropna()


def _safe_mean(df: pd.DataFrame, col: str) -> Optional[float]:
    s = _safe_series(df, col)
    if s.empty:
        return None
    return float(s.mean())


def _safe_max(df: pd.DataFrame, col: str) -> Optional[float]:
    s = _safe_series(df, col)
    if s.empty:
        return None
    return float(s.max())


def _safe_min(df: pd.DataFrame, col: str) -> Optional[float]:
    s = _safe_series(df, col)
    if s.empty:
        return None
    return float(s.min())


def _safe_abs_mean(df: pd.DataFrame, col: str) -> Optional[float]:
    s = _safe_series(df, col)
    if s.empty:
        return None
    return float(s.abs().mean())


def _safe_abs_max(df: pd.DataFrame, col: str) -> Optional[float]:
    s = _safe_series(df, col)
    if s.empty:
        return None
    return float(s.abs().max())


def _positive_max(df: pd.DataFrame, col: str) -> Optional[float]:
    s = _safe_series(df, col)
    s = s[s > 0]
    if s.empty:
        return 0.0
    return float(s.max())


def _negative_abs_max(df: pd.DataFrame, col: str) -> Optional[float]:
    s = _safe_series(df, col)
    s = s[s < 0]
    if s.empty:
        return 0.0
    return float(abs(s.min()))


def _path_length(df: pd.DataFrame, use_z: bool = True) -> Optional[float]:
    need = ["com_x", "com_y"] + (["com_z"] if use_z else [])
    if not set(need).issubset(df.columns) or len(df) < 2:
        return None
    sub = df[need].dropna().copy()
    if len(sub) < 2:
        return None
    dx = sub["com_x"].diff().fillna(0.0)
    dy = sub["com_y"].diff().fillna(0.0)
    if use_z:
        dz = sub["com_z"].diff().fillna(0.0)
        dist = (dx.pow(2) + dy.pow(2) + dz.pow(2)).pow(0.5)
    else:
        dist = (dx.pow(2) + dy.pow(2)).pow(0.5)
    return float(dist.sum())


def _displacement_components(df: pd.DataFrame):
    need = ["com_x", "com_y", "com_z"]
    if not set(need).issubset(df.columns):
        return None, None, None
    sub = df[need].dropna().copy()
    if len(sub) < 2:
        return None, None, None
    dx = float(sub["com_x"].iloc[-1] - sub["com_x"].iloc[0])
    dy = float(sub["com_y"].iloc[-1] - sub["com_y"].iloc[0])
    dz = float(sub["com_z"].iloc[-1] - sub["com_z"].iloc[0])
    return dx, dy, dz


def _euclidean_3d(dx, dy, dz):
    if dx is None or dy is None or dz is None:
        return None
    return float(math.sqrt(dx * dx + dy * dy + dz * dz))


def _horizontal_distance(dx, dy):
    if dx is None or dy is None:
        return None
    return float(math.sqrt(dx * dx + dy * dy))


def _classify_direction(dx: Optional[float], dy: Optional[float]) -> Optional[str]:
    if dx is None or dy is None:
        return None
    ax = abs(dx)
    ay = abs(dy)
    th = DIRECTION_COMPONENT_THRESHOLD_M
    if ax < th and ay < th:
        return "small_motion"
    if ax >= th and ay >= th:
        return "diagonal"
    if ax >= th:
        return "left_right"
    return "front_back"


def _component_metrics(prefix: str, df: pd.DataFrame) -> dict:
    dx, dy, dz = _displacement_components(df)
    direction_type = _classify_direction(dx, dy)
    horizontal = _horizontal_distance(dx, dy)
    return {
        f"{prefix}_dx_m": dx,
        f"{prefix}_dy_m": dy,
        f"{prefix}_dz_m": dz,
        f"{prefix}_left_right_distance_m": None if dx is None else abs(dx),
        f"{prefix}_front_back_distance_m": None if dy is None else abs(dy),
        f"{prefix}_diagonal_distance_m": horizontal if direction_type == "diagonal" and horizontal is not None else 0.0,
        f"{prefix}_horizontal_distance_m": horizontal,
        f"{prefix}_distance_m": _euclidean_3d(dx, dy, dz),
        f"{prefix}_direction_type": direction_type,
    }


def _duration_from_frames(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    if "time_s" in df.columns and len(df) >= 2:
        return float(df["time_s"].iloc[-1] - df["time_s"].iloc[0])
    return 0.0


def _count_runs(mask: pd.Series) -> int:
    if mask.empty:
        return 0
    vals = mask.fillna(False).astype(bool).tolist()
    count = 0
    i = 0
    n = len(vals)
    while i < n:
        if not vals[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and vals[j + 1]:
            j += 1
        if (j - i + 1) >= EVENT_MIN_FRAMES:
            count += 1
        i = j + 1
    return count


def _mask_time_seconds(df: pd.DataFrame, mask: pd.Series, fps_fallback: float = 60.0) -> float:
    if df.empty or mask.empty:
        return 0.0
    mask = mask.fillna(False).astype(bool)
    if not mask.any():
        return 0.0
    if "time_s" in df.columns and len(df) >= 2:
        dt = df["time_s"].diff().dropna()
        if not dt.empty:
            median_dt = float(dt.median())
            fps = round(1.0 / median_dt) if median_dt > 0 else fps_fallback
            return float(mask.sum()) / float(fps)
    return float(mask.sum()) / float(fps_fallback)


def _sum_step_events(df: pd.DataFrame) -> int:
    if df.empty or "step_event_count" not in df.columns:
        return 0
    s = pd.to_numeric(df["step_event_count"], errors="coerce").fillna(0)
    return int(s.sum())


def _step_frequency(step_count: int, duration_s: float) -> Optional[float]:
    if duration_s is None or duration_s <= 0:
        return None
    return float(step_count) / float(duration_s)


def _efficiency(net_distance: Optional[float], path_length: Optional[float]) -> Optional[float]:
    if net_distance is None or path_length is None or path_length <= 0:
        return None
    return float(net_distance) / float(path_length)


def _direction_change_metrics(prefix: str, df: pd.DataFrame) -> dict:
    flag_series = df.get("direction_change_flag", pd.Series(index=df.index, dtype=bool))
    flag_series = flag_series.fillna(False).astype(bool)
    return {
        f"{prefix}_direction_change_count": _count_runs(flag_series),
        f"{prefix}_mean_direction_change_speed_delta_mps": _safe_mean(df[flag_series], "direction_change_speed_delta_mps") if not df.empty else None,
        f"{prefix}_peak_direction_change_speed_delta_mps": _safe_max(df[flag_series], "direction_change_speed_delta_mps") if not df.empty else None,
        f"{prefix}_mean_direction_change_speed_rate_abs_mps2": _safe_mean(df[flag_series], "direction_change_speed_change_rate_abs_mps2") if not df.empty else None,
        f"{prefix}_peak_direction_change_speed_rate_abs_mps2": _safe_max(df[flag_series], "direction_change_speed_change_rate_abs_mps2") if not df.empty else None,
    }


def build_unit_metrics(frame_metrics: pd.DataFrame, step_metrics: pd.DataFrame | None = None, settings: dict | None = None) -> pd.DataFrame:
    if frame_metrics is None or frame_metrics.empty or "unit_id" not in frame_metrics.columns:
        return pd.DataFrame(columns=UNIT_COLUMNS)

    df = frame_metrics.copy()
    df = df[df["unit_id"].notna()].copy()
    if df.empty:
        return pd.DataFrame(columns=UNIT_COLUMNS)

    rows = []

    for raw_unit_id, unit_df in df.groupby("unit_id", sort=True):
        unit_df = unit_df.sort_values("frame_id").reset_index(drop=True)
        unit_id = int(raw_unit_id)

        move_df = unit_df[unit_df["phase_label"] == "move"].copy()
        restore_df = unit_df[unit_df["phase_label"] == "restore"].copy()

        left_total_mask = unit_df.get("left_support_state", pd.Series(index=unit_df.index, dtype=object)).eq("airborne")
        right_total_mask = unit_df.get("right_support_state", pd.Series(index=unit_df.index, dtype=object)).eq("airborne")
        left_single_mask = unit_df.get("support_mode", pd.Series(index=unit_df.index, dtype=object)).eq("left_airborne")
        right_single_mask = unit_df.get("support_mode", pd.Series(index=unit_df.index, dtype=object)).eq("right_airborne")
        double_mask = unit_df.get("support_mode", pd.Series(index=unit_df.index, dtype=object)).eq("double_airborne")

        move_step_count = _sum_step_events(move_df)
        restore_step_count = _sum_step_events(restore_df)
        unit_step_count = _sum_step_events(unit_df)

        move_duration_s = _duration_from_frames(move_df)
        restore_duration_s = _duration_from_frames(restore_df)
        unit_total_duration_s = _duration_from_frames(unit_df)

        row = {
            "unit_id": unit_id,
            "target_cell": int(unit_df["target_cell"].dropna().iloc[0]) if "target_cell" in unit_df.columns and not unit_df["target_cell"].dropna().empty else None,
            "move_start_frame": int(move_df["frame_id"].iloc[0]) if not move_df.empty else None,
            "move_end_frame": int(move_df["frame_id"].iloc[-1]) if not move_df.empty else None,
            "restore_start_frame": int(restore_df["frame_id"].iloc[0]) if not restore_df.empty else None,
            "restore_end_frame": int(restore_df["frame_id"].iloc[-1]) if not restore_df.empty else None,
            "move_duration_s": move_duration_s,
            "restore_duration_s": restore_duration_s,
            "unit_total_duration_s": unit_total_duration_s,
            "com_path_length_m": _path_length(unit_df, use_z=True),
            "com_horizontal_path_length_m": _path_length(unit_df, use_z=False),
            "trajectory_efficiency": None,
            "trajectory_efficiency_xy": None,
            "move_step_count": move_step_count,
            "restore_step_count": restore_step_count,
            "unit_step_count": unit_step_count,
            "move_step_frequency_hz": _step_frequency(move_step_count, move_duration_s),
            "restore_step_frequency_hz": _step_frequency(restore_step_count, restore_duration_s),
            "unit_step_frequency_hz": _step_frequency(unit_step_count, unit_total_duration_s),
            "move_mean_com_speed_mps": _safe_mean(move_df, "com_speed_mps"),
            "restore_mean_com_speed_mps": _safe_mean(restore_df, "com_speed_mps"),
            "move_peak_com_speed_mps": _safe_max(move_df, "com_speed_mps"),
            "restore_peak_com_speed_mps": _safe_max(restore_df, "com_speed_mps"),
            "left_airborne_count": _count_runs(left_total_mask),
            "right_airborne_count": _count_runs(right_total_mask),
            "left_airborne_time_s": _mask_time_seconds(unit_df, left_total_mask),
            "right_airborne_time_s": _mask_time_seconds(unit_df, right_total_mask),
            "left_single_airborne_count": _count_runs(left_single_mask),
            "right_single_airborne_count": _count_runs(right_single_mask),
            "left_single_airborne_time_s": _mask_time_seconds(unit_df, left_single_mask),
            "right_single_airborne_time_s": _mask_time_seconds(unit_df, right_single_mask),
            "double_airborne_count": _count_runs(double_mask),
            "double_airborne_time_s": _mask_time_seconds(unit_df, double_mask),
            "left_knee_max_deg": _safe_max(unit_df, "left_knee_angle_deg"),
            "right_knee_max_deg": _safe_max(unit_df, "right_knee_angle_deg"),
            "left_ankle_max_deg": _safe_max(unit_df, "left_ankle_angle_deg"),
            "right_ankle_max_deg": _safe_max(unit_df, "right_ankle_angle_deg"),
            "left_knee_min_deg": _safe_min(unit_df, "left_knee_angle_deg"),
            "right_knee_min_deg": _safe_min(unit_df, "right_knee_angle_deg"),
            "left_ankle_min_deg": _safe_min(unit_df, "left_ankle_angle_deg"),
            "right_ankle_min_deg": _safe_min(unit_df, "right_ankle_angle_deg"),
            "left_knee_mean_abs_angular_velocity_deg_s": _safe_abs_mean(unit_df, "left_knee_angular_velocity_deg_s"),
            "right_knee_mean_abs_angular_velocity_deg_s": _safe_abs_mean(unit_df, "right_knee_angular_velocity_deg_s"),
            "left_ankle_mean_abs_angular_velocity_deg_s": _safe_abs_mean(unit_df, "left_ankle_angular_velocity_deg_s"),
            "right_ankle_mean_abs_angular_velocity_deg_s": _safe_abs_mean(unit_df, "right_ankle_angular_velocity_deg_s"),
            "left_knee_peak_abs_angular_velocity_deg_s": _safe_abs_max(unit_df, "left_knee_angular_velocity_deg_s"),
            "right_knee_peak_abs_angular_velocity_deg_s": _safe_abs_max(unit_df, "right_knee_angular_velocity_deg_s"),
            "left_ankle_peak_abs_angular_velocity_deg_s": _safe_abs_max(unit_df, "left_ankle_angular_velocity_deg_s"),
            "right_ankle_peak_abs_angular_velocity_deg_s": _safe_abs_max(unit_df, "right_ankle_angular_velocity_deg_s"),
            "left_ankle_sagittal_max_deg": _safe_max(unit_df, "left_ankle_sagittal_angle_deg"),
            "right_ankle_sagittal_max_deg": _safe_max(unit_df, "right_ankle_sagittal_angle_deg"),
            "left_ankle_sagittal_min_deg": _safe_min(unit_df, "left_ankle_sagittal_angle_deg"),
            "right_ankle_sagittal_min_deg": _safe_min(unit_df, "right_ankle_sagittal_angle_deg"),
            "left_max_dorsiflexion_deg": _positive_max(unit_df, "left_ankle_sagittal_angle_deg"),
            "right_max_dorsiflexion_deg": _positive_max(unit_df, "right_ankle_sagittal_angle_deg"),
            "left_max_plantarflexion_deg": _negative_abs_max(unit_df, "left_ankle_sagittal_angle_deg"),
            "right_max_plantarflexion_deg": _negative_abs_max(unit_df, "right_ankle_sagittal_angle_deg"),
            "left_ankle_sagittal_mean_abs_angular_velocity_deg_s": _safe_abs_mean(unit_df, "left_ankle_sagittal_angular_velocity_deg_s"),
            "right_ankle_sagittal_mean_abs_angular_velocity_deg_s": _safe_abs_mean(unit_df, "right_ankle_sagittal_angular_velocity_deg_s"),
            "left_ankle_sagittal_peak_abs_angular_velocity_deg_s": _safe_abs_max(unit_df, "left_ankle_sagittal_angular_velocity_deg_s"),
            "right_ankle_sagittal_peak_abs_angular_velocity_deg_s": _safe_abs_max(unit_df, "right_ankle_sagittal_angular_velocity_deg_s"),
        }

        row.update(_component_metrics("move", move_df))
        row.update(_component_metrics("restore", restore_df))
        row.update(_direction_change_metrics("move", move_df))
        row.update(_direction_change_metrics("restore", restore_df))
        row.update(_direction_change_metrics("unit", unit_df))

        unit_dx, unit_dy, unit_dz = _displacement_components(unit_df)
        row.update({
            "unit_dx_m": unit_dx,
            "unit_dy_m": unit_dy,
            "unit_dz_m": unit_dz,
            "unit_left_right_distance_m": None if unit_dx is None else abs(unit_dx),
            "unit_front_back_distance_m": None if unit_dy is None else abs(unit_dy),
            "unit_horizontal_distance_m": _horizontal_distance(unit_dx, unit_dy),
            "unit_total_distance_m": _euclidean_3d(unit_dx, unit_dy, unit_dz),
        })

        if row["left_ankle_sagittal_max_deg"] is not None and row["left_ankle_sagittal_min_deg"] is not None:
            row["left_ankle_sagittal_range_deg"] = float(row["left_ankle_sagittal_max_deg"] - row["left_ankle_sagittal_min_deg"])
        else:
            row["left_ankle_sagittal_range_deg"] = None
        if row["right_ankle_sagittal_max_deg"] is not None and row["right_ankle_sagittal_min_deg"] is not None:
            row["right_ankle_sagittal_range_deg"] = float(row["right_ankle_sagittal_max_deg"] - row["right_ankle_sagittal_min_deg"])
        else:
            row["right_ankle_sagittal_range_deg"] = None

        row["trajectory_efficiency"] = _efficiency(row.get("unit_total_distance_m"), row.get("com_path_length_m"))
        row["trajectory_efficiency_xy"] = _efficiency(row.get("unit_horizontal_distance_m"), row.get("com_horizontal_path_length_m"))
        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=UNIT_COLUMNS)

    result = pd.DataFrame(rows)
    for col in UNIT_COLUMNS:
        if col not in result.columns:
            result[col] = pd.NA
    return result[UNIT_COLUMNS].copy()
