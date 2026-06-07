from __future__ import annotations

import math
from typing import Optional

import pandas as pd

from src.metrics.step.step_metrics_stub import STEP_COLUMNS


# ============================================================
# 【阈值可改】最短腾空步事件帧数
# ------------------------------------------------------------
# 某只脚从 takeoff 到 landing 的连续事件，若总帧数小于该值，则不记为一步。
# ============================================================
MIN_STEP_EVENT_FRAMES = 2


# ============================================================
# 【阈值可改】步幅方向分量判定阈值（单位：米）
# ------------------------------------------------------------
# 用于把一步的 COM 位移粗分为：左右 / 前后 / 斜向 / 小幅移动。
# ============================================================
STEP_DIRECTION_COMPONENT_THRESHOLD_M = 0.05


def _safe_mean(df: pd.DataFrame, col: str) -> Optional[float]:
    if col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return None
    return float(s.mean())


def _safe_max(df: pd.DataFrame, col: str) -> Optional[float]:
    if col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return None
    return float(s.max())


def _duration_s(df: pd.DataFrame) -> float:
    if df.empty or len(df) < 2:
        return 0.0
    if "time_s" in df.columns:
        return float(df["time_s"].iloc[-1] - df["time_s"].iloc[0])
    return 0.0


def _path_length(df: pd.DataFrame, use_z: bool = True) -> Optional[float]:
    need = ["com_x", "com_y"] + (["com_z"] if use_z else [])
    if not set(need).issubset(df.columns):
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


def _classify_direction(dx: Optional[float], dy: Optional[float]) -> Optional[str]:
    if dx is None or dy is None:
        return None
    ax = abs(dx)
    ay = abs(dy)
    th = STEP_DIRECTION_COMPONENT_THRESHOLD_M
    if ax < th and ay < th:
        return "small_motion"
    if ax >= th and ay >= th:
        return "diagonal"
    if ax >= th:
        return "left_right"
    return "front_back"


def _major_phase(segment_df: pd.DataFrame) -> Optional[str]:
    if "phase_label" not in segment_df.columns:
        return None
    s = segment_df["phase_label"].dropna()
    if s.empty:
        return None
    return s.mode().iloc[0]


def _major_unit_id(segment_df: pd.DataFrame):
    if "unit_id" not in segment_df.columns:
        return None
    s = segment_df["unit_id"].dropna()
    if s.empty:
        return None
    return s.mode().iloc[0]


def build_step_metrics(frame_metrics: pd.DataFrame) -> pd.DataFrame:
    if frame_metrics is None or frame_metrics.empty:
        return pd.DataFrame(columns=STEP_COLUMNS)

    df = frame_metrics.sort_values("frame_id").reset_index(drop=True).copy()
    rows = []
    step_id = 1

    last_landing_xy = {"left": None, "right": None}

    for foot_side in ["left", "right"]:
        state_col = f"{foot_side}_support_state"
        if state_col not in df.columns:
            continue

        states = df[state_col].fillna(method="ffill").fillna("support").tolist()
        takeoff_idx = None

        for i in range(1, len(df)):
            prev_state = states[i - 1]
            curr_state = states[i]

            # takeoff: support -> airborne
            if takeoff_idx is None and prev_state == "support" and curr_state == "airborne":
                takeoff_idx = i
                continue

            # landing: airborne -> support
            if takeoff_idx is not None and prev_state == "airborne" and curr_state == "support":
                landing_idx = i
                segment_df = df.iloc[takeoff_idx:landing_idx + 1].copy()

                if len(segment_df) >= MIN_STEP_EVENT_FRAMES:
                    dx, dy, dz = _displacement_components(segment_df)
                    horizontal_disp = None if dx is None or dy is None else float(math.sqrt(dx * dx + dy * dy))
                    total_disp = None if horizontal_disp is None or dz is None else float(math.sqrt(horizontal_disp * horizontal_disp + dz * dz))

                    landing_xy = None
                    if dx is not None and dy is not None:
                        landing_xy = (float(segment_df["com_x"].dropna().iloc[-1]), float(segment_df["com_y"].dropna().iloc[-1])) if not segment_df[["com_x", "com_y"]].dropna().empty else None

                    stride_length = None
                    if landing_xy is not None and last_landing_xy[foot_side] is not None:
                        px, py = last_landing_xy[foot_side]
                        lx, ly = landing_xy
                        stride_length = float(math.sqrt((lx - px) ** 2 + (ly - py) ** 2))
                    if landing_xy is not None:
                        last_landing_xy[foot_side] = landing_xy

                    row = {
                        "step_id": step_id,
                        "foot_side": foot_side,
                        "start_frame": int(segment_df["frame_id"].iloc[0]),
                        "end_frame": int(segment_df["frame_id"].iloc[-1]),
                        "duration_s": _duration_s(segment_df),
                        "swing_time_s": _duration_s(segment_df),
                        "stance_time_s": None,
                        "step_move_distance_m": _path_length(segment_df, use_z=True),
                        "step_horizontal_path_m": _path_length(segment_df, use_z=False),
                        "step_length_m": horizontal_disp,
                        "step_length_3d_m": total_disp,
                        "stride_length_m": stride_length,
                        "step_dx_m": dx,
                        "step_dy_m": dy,
                        "step_dz_m": dz,
                        "step_left_right_distance_m": None if dx is None else abs(dx),
                        "step_front_back_distance_m": None if dy is None else abs(dy),
                        "step_diagonal_distance_m": horizontal_disp if _classify_direction(dx, dy) == "diagonal" else 0.0,
                        "step_direction_type": _classify_direction(dx, dy),
                        "mean_foot_speed_mps": None,
                        "peak_foot_speed_mps": None,
                        "mean_com_speed_mps": _safe_mean(segment_df, "com_speed_mps"),
                        "mean_foot_acceleration_mps2": None,
                        "peak_foot_acceleration_mps2": None,
                        "mean_com_acceleration_mps2": _safe_mean(segment_df, "com_acceleration_mps2"),
                        "peak_com_acceleration_mps2": _safe_max(segment_df, "com_acceleration_mps2"),
                        "phase_label": _major_phase(segment_df),
                        "unit_id": _major_unit_id(segment_df),
                    }
                    rows.append(row)
                    step_id += 1

                takeoff_idx = None

    if not rows:
        return pd.DataFrame(columns=STEP_COLUMNS)

    result = pd.DataFrame(rows).sort_values("start_frame").reset_index(drop=True)
    for col in STEP_COLUMNS:
        if col not in result.columns:
            result[col] = pd.NA
    return result[STEP_COLUMNS].copy()
