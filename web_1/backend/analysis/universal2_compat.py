"""Compatibility helpers for exposing legacy CSV artifacts from Universal2 outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


LEGACY_STEP_COLUMNS = [
    "step_id",
    "foot_side",
    "start_frame",
    "end_frame",
    "duration_s",
    "swing_time_s",
    "stance_time_s",
    "step_move_distance_m",
    "step_horizontal_path_m",
    "step_length_m",
    "step_length_3d_m",
    "stride_length_m",
    "step_dx_m",
    "step_dy_m",
    "step_dz_m",
    "step_left_right_distance_m",
    "step_front_back_distance_m",
    "step_diagonal_distance_m",
    "step_direction_type",
    "mean_foot_speed_mps",
    "peak_foot_speed_mps",
    "mean_com_speed_mps",
    "mean_foot_acceleration_mps2",
    "peak_foot_acceleration_mps2",
    "mean_com_acceleration_mps2",
    "peak_com_acceleration_mps2",
    "phase_label",
    "unit_id",
]

LEGACY_UNIT_COLUMNS = [
    "unit_id",
    "target_cell",
    "move_start_frame",
    "move_end_frame",
    "restore_start_frame",
    "restore_end_frame",
    "move_duration_s",
    "restore_duration_s",
    "unit_total_duration_s",
    "move_dx_m",
    "move_dy_m",
    "move_dz_m",
    "move_left_right_distance_m",
    "move_front_back_distance_m",
    "move_diagonal_distance_m",
    "move_horizontal_distance_m",
    "move_distance_m",
    "move_direction_type",
    "restore_dx_m",
    "restore_dy_m",
    "restore_dz_m",
    "restore_left_right_distance_m",
    "restore_front_back_distance_m",
    "restore_diagonal_distance_m",
    "restore_horizontal_distance_m",
    "restore_distance_m",
    "restore_direction_type",
    "unit_dx_m",
    "unit_dy_m",
    "unit_dz_m",
    "unit_left_right_distance_m",
    "unit_front_back_distance_m",
    "unit_horizontal_distance_m",
    "unit_total_distance_m",
    "com_path_length_m",
    "com_horizontal_path_length_m",
    "trajectory_efficiency",
    "trajectory_efficiency_xy",
    "move_step_count",
    "restore_step_count",
    "unit_step_count",
    "move_step_frequency_hz",
    "restore_step_frequency_hz",
    "unit_step_frequency_hz",
]


def _safe_num_series(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def _safe_scalar(v: Any) -> float | int | None:
    if v is None:
        return None
    if pd.isna(v):
        return None
    x = float(v)
    if float(x).is_integer():
        return int(x)
    return x


def _legacy_frame_metrics(frame_df: pd.DataFrame) -> pd.DataFrame:
    out = frame_df.copy()

    if "turning_speed_deg_s" not in out.columns:
        if "motion_turning_speed_deg_s" in out.columns:
            out["turning_speed_deg_s"] = out["motion_turning_speed_deg_s"]
        else:
            out["turning_speed_deg_s"] = 0.0
    if "motion_heading_deg" not in out.columns:
        out["motion_heading_deg"] = 0.0
    if "motion_turning_speed_deg_s" not in out.columns:
        out["motion_turning_speed_deg_s"] = out["turning_speed_deg_s"]
    if "direction_change_flag" not in out.columns:
        out["direction_change_flag"] = 0
    if "direction_change_speed_delta_mps" not in out.columns:
        out["direction_change_speed_delta_mps"] = 0.0
    if "direction_change_speed_change_rate_abs_mps2" not in out.columns:
        out["direction_change_speed_change_rate_abs_mps2"] = 0.0
    if "left_ankle_motion_label" not in out.columns:
        out["left_ankle_motion_label"] = ""
    if "right_ankle_motion_label" not in out.columns:
        out["right_ankle_motion_label"] = ""
    if "phase_label" not in out.columns:
        out["phase_label"] = out.get("movement_state", "")
    if "unit_id" not in out.columns:
        out["unit_id"] = out.get("cycle_id", pd.NA)
    if "target_cell" not in out.columns:
        out["target_cell"] = pd.NA

    preferred_cols = [
        "frame_id",
        "time_s",
        "com_x",
        "com_y",
        "com_z",
        "com_cell",
        "com_speed_mps",
        "com_horizontal_speed_mps",
        "com_acceleration_mps2",
        "turning_speed_deg_s",
        "motion_heading_deg",
        "motion_turning_speed_deg_s",
        "direction_change_flag",
        "direction_change_speed_delta_mps",
        "direction_change_speed_change_rate_abs_mps2",
        "left_clearance_m",
        "right_clearance_m",
        "left_knee_angle_deg",
        "right_knee_angle_deg",
        "left_ankle_angle_deg",
        "right_ankle_angle_deg",
        "left_ankle_sagittal_angle_deg",
        "right_ankle_sagittal_angle_deg",
        "left_ankle_motion_label",
        "right_ankle_motion_label",
        "left_knee_angular_velocity_deg_s",
        "right_knee_angular_velocity_deg_s",
        "left_ankle_angular_velocity_deg_s",
        "right_ankle_angular_velocity_deg_s",
        "left_ankle_sagittal_angular_velocity_deg_s",
        "right_ankle_sagittal_angular_velocity_deg_s",
        "left_support_state",
        "right_support_state",
        "support_mode",
        "left_landing_event",
        "right_landing_event",
        "step_event_count",
        "phase_label",
        "unit_id",
        "target_cell",
    ]
    existing = [c for c in preferred_cols if c in out.columns]
    extras = [c for c in out.columns if c not in existing]
    return out[existing + extras]


def _legacy_step_metrics(state_event_df: pd.DataFrame, speed_summary_df: pd.DataFrame) -> pd.DataFrame:
    if not speed_summary_df.empty:
        return speed_summary_df.copy()
    if state_event_df.empty:
        return pd.DataFrame(columns=LEGACY_STEP_COLUMNS)
    return state_event_df.copy()


def _legacy_unit_metrics(state_event_df: pd.DataFrame) -> pd.DataFrame:
    if state_event_df.empty:
        return pd.DataFrame(columns=LEGACY_UNIT_COLUMNS)

    unit_df = state_event_df.copy()
    rename_map = {
        "循环序号": "unit_id",
        "目标格": "target_cell",
        "状态1_时长_s": "move_duration_s",
        "状态2_时长_s": "pause_duration_s",
        "状态3_时长_s": "restore_duration_s",
    }
    for src, dst in rename_map.items():
        if src in unit_df.columns:
            unit_df[dst] = unit_df[src]
    if "move_duration_s" in unit_df.columns and "restore_duration_s" in unit_df.columns:
        unit_df["unit_total_duration_s"] = (
            pd.to_numeric(unit_df["move_duration_s"], errors="coerce").fillna(0.0)
            + pd.to_numeric(unit_df["restore_duration_s"], errors="coerce").fillna(0.0)
        )
    return unit_df


def _legacy_session_summary(
    frame_df: pd.DataFrame,
    overall_summary_df: pd.DataFrame,
    evaluation_summary_df: pd.DataFrame,
    torque_summary_df: pd.DataFrame,
    segmentation_diagnostics: dict[str, Any] | None = None,
) -> pd.DataFrame:
    row: dict[str, Any] = {}

    if not overall_summary_df.empty:
        row.update(overall_summary_df.iloc[0].to_dict())
    if not evaluation_summary_df.empty:
        row.update(evaluation_summary_df.iloc[0].to_dict())
    if not torque_summary_df.empty:
        row.update(torque_summary_df.iloc[0].to_dict())

    frame_count = int(len(frame_df))
    row["total_frames"] = frame_count
    t = _safe_num_series(frame_df, "time_s").dropna()
    row["total_duration_s"] = float(t.iloc[-1] - t.iloc[0]) if len(t) >= 2 else 0.0

    cycle_count = pd.to_numeric(frame_df.get("cycle_id", pd.Series(dtype=float)), errors="coerce").dropna().nunique()
    row["unit_count"] = int(cycle_count)
    row["total_step_count"] = int(pd.to_numeric(frame_df.get("step_event_count", 0), errors="coerce").fillna(0).sum())

    com_speed = _safe_num_series(frame_df, "com_speed_mps").dropna()
    com_acc = _safe_num_series(frame_df, "com_acceleration_mps2").dropna()
    row["mean_com_speed_mps"] = _safe_scalar(com_speed.mean()) if not com_speed.empty else 0.0
    row["peak_com_speed_mps"] = _safe_scalar(com_speed.max()) if not com_speed.empty else 0.0
    row["mean_com_acceleration_mps2"] = _safe_scalar(com_acc.mean()) if not com_acc.empty else 0.0
    row["peak_com_acceleration_mps2"] = _safe_scalar(com_acc.abs().max()) if not com_acc.empty else 0.0

    left_c = _safe_num_series(frame_df, "left_clearance_m").dropna()
    right_c = _safe_num_series(frame_df, "right_clearance_m").dropna()
    row["left_clearance_peak_m"] = _safe_scalar(left_c.max()) if not left_c.empty else 0.0
    row["right_clearance_peak_m"] = _safe_scalar(right_c.max()) if not right_c.empty else 0.0

    left_knee = _safe_num_series(frame_df, "left_knee_angle_deg").dropna()
    right_knee = _safe_num_series(frame_df, "right_knee_angle_deg").dropna()
    left_ankle = _safe_num_series(frame_df, "left_ankle_angle_deg").dropna()
    right_ankle = _safe_num_series(frame_df, "right_ankle_angle_deg").dropna()
    row["left_knee_angle_max_deg"] = _safe_scalar(left_knee.max()) if not left_knee.empty else None
    row["right_knee_angle_max_deg"] = _safe_scalar(right_knee.max()) if not right_knee.empty else None
    row["left_ankle_angle_max_deg"] = _safe_scalar(left_ankle.max()) if not left_ankle.empty else None
    row["right_ankle_angle_max_deg"] = _safe_scalar(right_ankle.max()) if not right_ankle.empty else None

    # Preserve numeric compatibility for legacy payload consumers.
    for k, v in list(row.items()):
        if isinstance(v, (np.floating, np.integer)):
            row[k] = _safe_scalar(v)

    seg = dict(segmentation_diagnostics or {})
    row["segmentation_status"] = str(seg.get("segmentation_status", "unknown"))
    row["segmentation_reason"] = str(seg.get("segmentation_reason", ""))
    row["segmentation_source"] = str(seg.get("segmentation_source", ""))
    row["segmentation_cycle_count"] = _safe_scalar(seg.get("cycle_count", row.get("unit_count", 0)))
    row["segmentation_non_home_cell_frames"] = _safe_scalar(seg.get("non_home_cell_frames", 0))
    row["segmentation_analysis_active_ratio"] = _safe_scalar(seg.get("analysis_active_ratio", 0.0))
    row["segmentation_moving_signal_ratio"] = _safe_scalar(seg.get("moving_signal_ratio", 0.0))
    row["segmentation_moving_required_ratio"] = _safe_scalar(seg.get("moving_signal_required_ratio", 0.0))
    row["segmentation_confidence"] = str(seg.get("segmentation_confidence", "none"))
    row["segmentation_fallback_level"] = str(seg.get("fallback_level", "none"))

    return pd.DataFrame([row])


def write_legacy_csv_bundle(
    *,
    output_dir: Path,
    frame_df: pd.DataFrame,
    state_event_df: pd.DataFrame,
    speed_summary_df: pd.DataFrame,
    overall_summary_df: pd.DataFrame,
    evaluation_summary_df: pd.DataFrame,
    torque_summary_df: pd.DataFrame,
    segmentation_diagnostics: dict[str, Any] | None = None,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    legacy_frame_df = _legacy_frame_metrics(frame_df)
    legacy_step_df = _legacy_step_metrics(state_event_df, speed_summary_df)
    legacy_unit_df = _legacy_unit_metrics(state_event_df)
    legacy_session_df = _legacy_session_summary(
        frame_df=frame_df,
        overall_summary_df=overall_summary_df,
        evaluation_summary_df=evaluation_summary_df,
        torque_summary_df=torque_summary_df,
        segmentation_diagnostics=segmentation_diagnostics,
    )

    legacy_frame_df.to_csv(output_dir / "frame_metrics.csv", index=False, encoding="utf-8-sig")
    legacy_step_df.to_csv(output_dir / "step_metrics.csv", index=False, encoding="utf-8-sig")
    legacy_unit_df.to_csv(output_dir / "unit_metrics.csv", index=False, encoding="utf-8-sig")
    legacy_session_df.to_csv(output_dir / "session_summary.csv", index=False, encoding="utf-8-sig")
