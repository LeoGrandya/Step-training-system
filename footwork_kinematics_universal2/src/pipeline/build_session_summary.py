import math

import pandas as pd


def _safe_stat(df: pd.DataFrame, col: str, stat: str):
    if df is None or col not in df.columns or df[col].dropna().empty:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return None
    if stat == "mean":
        return float(s.mean())
    if stat == "max":
        return float(s.max())
    if stat == "min":
        return float(s.min())
    if stat == "sum":
        return float(s.sum())
    if stat == "abs_mean":
        return float(s.abs().mean())
    if stat == "abs_max":
        return float(s.abs().max())
    return None


def _path_length(frame_metrics: pd.DataFrame, use_z: bool = True):
    need = ["com_x", "com_y"] + (["com_z"] if use_z else [])
    if frame_metrics is None or frame_metrics.empty or not set(need).issubset(frame_metrics.columns):
        return None
    sub = frame_metrics[need].dropna().copy()
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


def _path_component_sum(frame_metrics: pd.DataFrame, col: str):
    if frame_metrics is None or frame_metrics.empty or col not in frame_metrics.columns:
        return None
    s = pd.to_numeric(frame_metrics[col], errors="coerce")
    if s.dropna().empty:
        return None
    return float(s.diff().abs().fillna(0.0).sum())


def _net_displacement(frame_metrics: pd.DataFrame, use_z: bool = True):
    need = ["com_x", "com_y"] + (["com_z"] if use_z else [])
    if frame_metrics is None or frame_metrics.empty or not set(need).issubset(frame_metrics.columns):
        return None
    sub = frame_metrics[need].dropna().copy()
    if len(sub) < 2:
        return None
    dx = float(sub["com_x"].iloc[-1] - sub["com_x"].iloc[0])
    dy = float(sub["com_y"].iloc[-1] - sub["com_y"].iloc[0])
    if use_z:
        dz = float(sub["com_z"].iloc[-1] - sub["com_z"].iloc[0])
        return float(math.sqrt(dx * dx + dy * dy + dz * dz))
    return float(math.sqrt(dx * dx + dy * dy))


def _efficiency(net_distance, path_length):
    if net_distance is None or path_length is None or path_length <= 0:
        return None
    return float(net_distance) / float(path_length)


def _calc_total_move_count(frame_metrics: pd.DataFrame, unit_metrics: pd.DataFrame) -> int:
    if unit_metrics is not None and not unit_metrics.empty:
        return int(len(unit_metrics))
    if frame_metrics is not None and not frame_metrics.empty and "unit_id" in frame_metrics.columns:
        return int(frame_metrics["unit_id"].dropna().nunique())
    return 0


def _calc_total_step_count(frame_metrics: pd.DataFrame, unit_metrics: pd.DataFrame) -> int:
    if frame_metrics is not None and not frame_metrics.empty and "step_event_count" in frame_metrics.columns:
        s = pd.to_numeric(frame_metrics["step_event_count"], errors="coerce").fillna(0)
        return int(s.sum())
    if unit_metrics is not None and not unit_metrics.empty and "unit_step_count" in unit_metrics.columns:
        s = pd.to_numeric(unit_metrics["unit_step_count"], errors="coerce").fillna(0)
        return int(s.sum())
    return 0


def _positive_max(frame_metrics: pd.DataFrame, col: str):
    if frame_metrics is None or frame_metrics.empty or col not in frame_metrics.columns:
        return None
    s = pd.to_numeric(frame_metrics[col], errors="coerce")
    s = s[s > 0].dropna()
    if s.empty:
        return 0.0
    return float(s.max())


def _negative_abs_max(frame_metrics: pd.DataFrame, col: str):
    if frame_metrics is None or frame_metrics.empty or col not in frame_metrics.columns:
        return None
    s = pd.to_numeric(frame_metrics[col], errors="coerce")
    s = s[s < 0].dropna()
    if s.empty:
        return 0.0
    return float(abs(s.min()))


def build_session_summary(frame_metrics, step_metrics, unit_metrics) -> pd.DataFrame:
    total_path_length_m = _path_length(frame_metrics, use_z=True)
    total_horizontal_path_length_m = _path_length(frame_metrics, use_z=False)
    total_net_displacement_m = _net_displacement(frame_metrics, use_z=True)
    total_horizontal_net_displacement_m = _net_displacement(frame_metrics, use_z=False)

    direction_change_flags = 0
    if frame_metrics is not None and not frame_metrics.empty and "direction_change_flag" in frame_metrics.columns:
        flags = frame_metrics["direction_change_flag"].fillna(False).astype(bool)
        prev = flags.shift(1).fillna(False)
        direction_change_flags = int(((~prev) & flags).sum())

    row = {
        "total_frames": int(len(frame_metrics)),
        "total_duration_s": float(frame_metrics["time_s"].max()) if "time_s" in frame_metrics.columns and not frame_metrics.empty else 0.0,
        "unit_count": int(len(unit_metrics)),
        "step_count": int(len(step_metrics)) if step_metrics is not None else 0,
        "total_move_count": _calc_total_move_count(frame_metrics, unit_metrics),
        "total_step_count": _calc_total_step_count(frame_metrics, unit_metrics),
        "total_path_length_m": total_path_length_m,
        "total_horizontal_path_length_m": total_horizontal_path_length_m,
        "total_left_right_path_m": _path_component_sum(frame_metrics, "com_x"),
        "total_front_back_path_m": _path_component_sum(frame_metrics, "com_y"),
        "total_vertical_path_m": _path_component_sum(frame_metrics, "com_z"),
        "total_net_displacement_m": total_net_displacement_m,
        "total_horizontal_net_displacement_m": total_horizontal_net_displacement_m,
        "trajectory_efficiency": _efficiency(total_net_displacement_m, total_path_length_m),
        "trajectory_efficiency_xy": _efficiency(total_horizontal_net_displacement_m, total_horizontal_path_length_m),
        "step_length_mean_m": _safe_stat(step_metrics, "step_length_m", "mean"),
        "step_length_max_m": _safe_stat(step_metrics, "step_length_m", "max"),
        "step_horizontal_path_mean_m": _safe_stat(step_metrics, "step_horizontal_path_m", "mean"),
        "mean_com_speed_mps": _safe_stat(frame_metrics, "com_speed_mps", "mean"),
        "peak_com_speed_mps": _safe_stat(frame_metrics, "com_speed_mps", "max"),
        "mean_com_acceleration_mps2": _safe_stat(frame_metrics, "com_acceleration_mps2", "mean"),
        "peak_com_acceleration_mps2": _safe_stat(frame_metrics, "com_acceleration_mps2", "max"),
        "mean_direction_change_speed_delta_mps": _safe_stat(frame_metrics, "direction_change_speed_delta_mps", "mean"),
        "peak_direction_change_speed_delta_mps": _safe_stat(frame_metrics, "direction_change_speed_delta_mps", "max"),
        "mean_direction_change_speed_rate_abs_mps2": _safe_stat(frame_metrics, "direction_change_speed_change_rate_abs_mps2", "mean"),
        "peak_direction_change_speed_rate_abs_mps2": _safe_stat(frame_metrics, "direction_change_speed_change_rate_abs_mps2", "max"),
        "direction_change_count": direction_change_flags,
        "left_clearance_peak_m": _safe_stat(frame_metrics, "left_clearance_m", "max"),
        "right_clearance_peak_m": _safe_stat(frame_metrics, "right_clearance_m", "max"),
        "left_knee_angle_max_deg": _safe_stat(frame_metrics, "left_knee_angle_deg", "max"),
        "right_knee_angle_max_deg": _safe_stat(frame_metrics, "right_knee_angle_deg", "max"),
        "left_ankle_angle_max_deg": _safe_stat(frame_metrics, "left_ankle_angle_deg", "max"),
        "right_ankle_angle_max_deg": _safe_stat(frame_metrics, "right_ankle_angle_deg", "max"),
        "left_knee_mean_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "left_knee_angular_velocity_deg_s", "abs_mean"),
        "right_knee_mean_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "right_knee_angular_velocity_deg_s", "abs_mean"),
        "left_ankle_mean_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "left_ankle_angular_velocity_deg_s", "abs_mean"),
        "right_ankle_mean_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "right_ankle_angular_velocity_deg_s", "abs_mean"),
        "left_knee_peak_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "left_knee_angular_velocity_deg_s", "abs_max"),
        "right_knee_peak_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "right_knee_angular_velocity_deg_s", "abs_max"),
        "left_ankle_peak_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "left_ankle_angular_velocity_deg_s", "abs_max"),
        "right_ankle_peak_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "right_ankle_angular_velocity_deg_s", "abs_max"),
        "left_ankle_sagittal_max_deg": _safe_stat(frame_metrics, "left_ankle_sagittal_angle_deg", "max"),
        "right_ankle_sagittal_max_deg": _safe_stat(frame_metrics, "right_ankle_sagittal_angle_deg", "max"),
        "left_ankle_sagittal_min_deg": _safe_stat(frame_metrics, "left_ankle_sagittal_angle_deg", "min"),
        "right_ankle_sagittal_min_deg": _safe_stat(frame_metrics, "right_ankle_sagittal_angle_deg", "min"),
        "left_max_dorsiflexion_deg": _positive_max(frame_metrics, "left_ankle_sagittal_angle_deg"),
        "right_max_dorsiflexion_deg": _positive_max(frame_metrics, "right_ankle_sagittal_angle_deg"),
        "left_max_plantarflexion_deg": _negative_abs_max(frame_metrics, "left_ankle_sagittal_angle_deg"),
        "right_max_plantarflexion_deg": _negative_abs_max(frame_metrics, "right_ankle_sagittal_angle_deg"),
        "left_ankle_sagittal_mean_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "left_ankle_sagittal_angular_velocity_deg_s", "abs_mean"),
        "right_ankle_sagittal_mean_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "right_ankle_sagittal_angular_velocity_deg_s", "abs_mean"),
        "left_ankle_sagittal_peak_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "left_ankle_sagittal_angular_velocity_deg_s", "abs_max"),
        "right_ankle_sagittal_peak_abs_angular_velocity_deg_s": _safe_stat(frame_metrics, "right_ankle_sagittal_angular_velocity_deg_s", "abs_max"),
    }

    if row["left_ankle_sagittal_max_deg"] is not None and row["left_ankle_sagittal_min_deg"] is not None:
        row["left_ankle_sagittal_range_deg"] = float(row["left_ankle_sagittal_max_deg"] - row["left_ankle_sagittal_min_deg"])
    else:
        row["left_ankle_sagittal_range_deg"] = None
    if row["right_ankle_sagittal_max_deg"] is not None and row["right_ankle_sagittal_min_deg"] is not None:
        row["right_ankle_sagittal_range_deg"] = float(row["right_ankle_sagittal_max_deg"] - row["right_ankle_sagittal_min_deg"])
    else:
        row["right_ankle_sagittal_range_deg"] = None

    return pd.DataFrame([row])
