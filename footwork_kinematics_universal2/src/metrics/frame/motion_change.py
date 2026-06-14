import numpy as np
import pandas as pd


# ============================================================
# 【阈值可改】最小水平速度阈值（单位：m/s）
# ------------------------------------------------------------
# 当 COM 水平速度过小时，运动方向角非常容易抖动，因此不认为处于有效变向分析状态。
# ============================================================
MIN_HORIZONTAL_SPEED_MPS = 0.20


# ============================================================
# 【阈值可改】变向判定阈值（单位：deg/s）
# ------------------------------------------------------------
# 当 COM 运动方向角速度超过该阈值时，认为进入“变向帧”。
# ============================================================
MOTION_TURN_THRESHOLD_DEG_S = 30.0


def _wrap_deg(angle_deg: pd.Series) -> pd.Series:
    return ((angle_deg + 180.0) % 360.0) - 180.0


def compute_motion_change_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算“变向时线速度变化”相关指标。

    输出列：
    - com_horizontal_speed_mps: COM 水平速度
    - motion_heading_deg: COM 水平运动方向角
    - motion_turning_speed_deg_s: COM 水平运动方向角速度
    - direction_change_flag: 是否处于变向帧
    - direction_change_speed_delta_mps: 变向帧上的水平速度变化量 |Δv|
    - direction_change_speed_change_rate_abs_mps2: 变向帧上的水平速度变化率 |Δv/Δt|
    """
    out = pd.DataFrame({"frame_id": df["frame_id"]})

    required = ["com_x", "com_y", "time_s"]
    if not all(c in df.columns for c in required):
        out["com_horizontal_speed_mps"] = pd.NA
        out["motion_heading_deg"] = pd.NA
        out["motion_turning_speed_deg_s"] = pd.NA
        out["direction_change_flag"] = False
        out["direction_change_speed_delta_mps"] = 0.0
        out["direction_change_speed_change_rate_abs_mps2"] = 0.0
        return out

    dx = pd.to_numeric(df["com_x"], errors="coerce").diff()
    dy = pd.to_numeric(df["com_y"], errors="coerce").diff()
    dt = pd.to_numeric(df["time_s"], errors="coerce").diff()

    horizontal_speed = np.sqrt(dx.pow(2) + dy.pow(2)) / dt
    horizontal_speed = horizontal_speed.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    heading = np.degrees(np.arctan2(dy, dx))
    heading = pd.Series(heading, index=df.index, name="motion_heading_deg")

    valid_now = horizontal_speed >= MIN_HORIZONTAL_SPEED_MPS
    valid_prev = valid_now.shift(1).fillna(False)
    valid_turn = valid_now & valid_prev

    d_heading = _wrap_deg(heading.diff())
    motion_turning_speed = d_heading / dt
    motion_turning_speed = motion_turning_speed.replace([np.inf, -np.inf], np.nan)
    motion_turning_speed = motion_turning_speed.where(valid_turn, 0.0).fillna(0.0)

    direction_change_flag = valid_turn & (motion_turning_speed.abs() >= MOTION_TURN_THRESHOLD_DEG_S)

    speed_delta_abs = horizontal_speed.diff().abs().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    speed_change_rate_abs = (horizontal_speed.diff() / dt).abs().replace([np.inf, -np.inf], np.nan).fillna(0.0)

    out["com_horizontal_speed_mps"] = horizontal_speed
    out["motion_heading_deg"] = heading.ffill()
    out["motion_turning_speed_deg_s"] = motion_turning_speed
    out["direction_change_flag"] = direction_change_flag.fillna(False).astype(bool)
    out["direction_change_speed_delta_mps"] = speed_delta_abs.where(out["direction_change_flag"], 0.0)
    out["direction_change_speed_change_rate_abs_mps2"] = speed_change_rate_abs.where(out["direction_change_flag"], 0.0)
    return out
