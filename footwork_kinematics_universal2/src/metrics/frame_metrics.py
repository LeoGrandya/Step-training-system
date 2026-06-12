# -*- coding: utf-8 -*-
"""
逐帧运动学指标计算模块。

输入：滤波后的宽表 frame_df（每帧一行，含所有关节 x/y/z 及 com_x/y/z）
输出：附加了所有逐帧指标的 DataFrame。

所有原始数据先经 Butterworth 滤波，再进入差分计算。
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

from src.grid.nine_grid import (
    estimate_ground_z,
    estimate_grid_center_xy,
    locate_cell_absolute,
)


def _derivative(series: pd.Series, dt: float) -> pd.Series:
    """中心差分法计算一阶导数 (np.gradient)。"""
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().empty or dt <= 0:
        return pd.Series(np.nan, index=s.index, dtype=float)
    arr = s.interpolate(limit_direction="both").to_numpy(dtype=float)
    der = np.gradient(arr, dt)
    result = pd.Series(der, index=s.index, dtype=float)
    result[s.isna()] = np.nan
    return result


def _vector_angle_deg(v1: np.ndarray, v2: np.ndarray) -> float:
    """两个三维向量之间的夹角（度）。"""
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return np.nan
    if not np.isfinite(v1).all() or not np.isfinite(v2).all():
        return np.nan
    cos_val = np.dot(v1, v2) / (n1 * n2)
    cos_val = np.clip(cos_val, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_val)))


def _consecutive_lengths(values: list) -> list:
    """连续相同值的长度列表。"""
    out = []
    last = object()
    count = 0
    for v in values:
        same = (pd.isna(v) and pd.isna(last)) or (v == last)
        if same:
            count += 1
        else:
            count = 1
            last = v
        out.append(count)
    return out


def build_frame_metrics(
    frame_df: pd.DataFrame,
    params: dict,
) -> pd.DataFrame:
    """
    构建所有逐帧运动学指标。

    返回的 DataFrame 包含：
    - 基础：frame_id, time_s
    - COM：com_x/y/z, com_vx/vy/vz, com_speed_mps, com_horizontal_speed_mps,
            com_acceleration_mps2, com_disp_x_m, com_disp_y_m, com_cell
    - 脚踝：left/right_ankle 的 speed, acceleration, vx, vy
    - 离地高度：left/right_foot_avg_z_m, left/right_clearance_m
    - 支撑：left/right_support_state, support_mode, left/right_landing_event
    - 关节角：hip/knee/ankle angle, angular velocity, angular acceleration
    - 小腿倾斜角：left/right_shank_tilt_angle_deg
    - 躯干法向量波动：trunk_tilt_rate_deg_s
    """
    fps = float(params.get("fps", 60.0))
    dt = 1.0 / fps if fps > 0 else 0.0

    df = frame_df.copy()

    # ============================
    # 1. 地面 & 九宫格
    # ============================
    ground_z = params.get("ground_z")
    if ground_z is None:
        ground_z = estimate_ground_z(df)

    grid_cfg = params.get("grid", {})
    center_xy = grid_cfg.get("center_xy")
    if not center_xy:
        center_xy = estimate_grid_center_xy(df, grid_cfg.get("center_estimate_frames", 60))
    center_xy = (float(center_xy[0]), float(center_xy[1]))
    cell_size = float(grid_cfg.get("cell_size_m", 0.9))
    total_size = float(grid_cfg.get("total_size_m", 2.7))

    # ============================
    # 2. 足底高度 & 离地高度
    # ============================
    for side in ["left", "right"]:
        heel_col = f"{side}_heel_z"
        toe_col = f"{side}_foot_index_z"
        df[f"{side}_foot_avg_z_m"] = df[[heel_col, toe_col]].mean(axis=1)
        df[f"{side}_clearance_m"] = (df[f"{side}_foot_avg_z_m"] - float(ground_z)).clip(lower=0.0)

    # ============================
    # 3. 速度 & 加速度（COM + 左右脚踝）
    # ============================
    for prefix in ["com", "left_ankle", "right_ankle"]:
        x_col = f"{prefix}_x"
        y_col = f"{prefix}_y"
        z_col = f"{prefix}_z"

        # 单轴速度
        df[f"{prefix}_vx_mps"] = _derivative(df[x_col], dt)
        df[f"{prefix}_vy_mps"] = _derivative(df[y_col], dt)
        df[f"{prefix}_vz_mps"] = _derivative(df[z_col], dt)

        # 合速度（3D）
        df[f"{prefix}_speed_mps"] = np.sqrt(
            df[f"{prefix}_vx_mps"] ** 2
            + df[f"{prefix}_vy_mps"] ** 2
            + df[f"{prefix}_vz_mps"] ** 2
        )

        # 水平合速度
        df[f"{prefix}_horizontal_speed_mps"] = np.sqrt(
            df[f"{prefix}_vx_mps"] ** 2
            + df[f"{prefix}_vy_mps"] ** 2
        )

        # 合加速度
        df[f"{prefix}_acceleration_mps2"] = _derivative(df[f"{prefix}_speed_mps"], dt)

        # 绝对速度分量（用于统计均值）
        df[f"{prefix}_vx_abs_mps"] = df[f"{prefix}_vx_mps"].abs()
        df[f"{prefix}_vy_abs_mps"] = df[f"{prefix}_vy_mps"].abs()

    # ============================
    # 4. 位移（相对第0帧）+ 水平路径累计距离
    # ============================
    for prefix in ["com", "left_ankle", "right_ankle"]:
        x_col = f"{prefix}_x"
        y_col = f"{prefix}_y"
        x0 = df[x_col].dropna().iloc[0] if not df[x_col].dropna().empty else 0.0
        y0 = df[y_col].dropna().iloc[0] if not df[y_col].dropna().empty else 0.0
        df[f"{prefix}_disp_x_m"] = df[x_col] - x0
        df[f"{prefix}_disp_y_m"] = df[y_col] - y0
        dx = df[x_col].diff().fillna(0)
        dy = df[y_col].diff().fillna(0)
        df[f"{prefix}_horizontal_path_m"] = np.sqrt(dx ** 2 + dy ** 2).cumsum()

    # ============================
    # 5. 九宫格定位（COM / 左右脚踝）
    # ============================
    for prefix in ["com", "left_ankle", "right_ankle"]:
        df[f"{prefix}_cell"] = df.apply(
            lambda r: locate_cell_absolute(
                r[f"{prefix}_x"], r[f"{prefix}_y"],
                center_xy, cell_size, total_size,
            ) if pd.notna(r[f"{prefix}_x"]) and pd.notna(r[f"{prefix}_y"]) else pd.NA,
            axis=1,
        )

    # ============================
    # 6. 关节角度（髋 / 膝 / 踝）
    # ============================
    # 遍历每帧计算
    hip_left, hip_right = [], []
    knee_left, knee_right = [], []
    ankle_left, ankle_right = [], []
    shank_tilt_left, shank_tilt_right = [], []
    trunk_tilt = []

    for _, row in df.iterrows():
        lh = np.array([row["left_hip_x"], row["left_hip_y"], row["left_hip_z"]], dtype=float)
        rh = np.array([row["right_hip_x"], row["right_hip_y"], row["right_hip_z"]], dtype=float)
        lk = np.array([row["left_knee_x"], row["left_knee_y"], row["left_knee_z"]], dtype=float)
        rk = np.array([row["right_knee_x"], row["right_knee_y"], row["right_knee_z"]], dtype=float)
        la = np.array([row["left_ankle_x"], row["left_ankle_y"], row["left_ankle_z"]], dtype=float)
        ra = np.array([row["right_ankle_x"], row["right_ankle_y"], row["right_ankle_z"]], dtype=float)
        ls = np.array([row["left_shoulder_x"], row["left_shoulder_y"], row["left_shoulder_z"]], dtype=float)
        rs = np.array([row["right_shoulder_x"], row["right_shoulder_y"], row["right_shoulder_z"]], dtype=float)
        lheel = np.array([row["left_heel_x"], row["left_heel_y"], row["left_heel_z"]], dtype=float)
        rheel = np.array([row["right_heel_x"], row["right_heel_y"], row["right_heel_z"]], dtype=float)
        ltoe = np.array([row["left_foot_index_x"], row["left_foot_index_y"], row["left_foot_index_z"]], dtype=float)
        rtoe = np.array([row["right_foot_index_x"], row["right_foot_index_y"], row["right_foot_index_z"]], dtype=float)

        # 髋关节角: 髋→膝 与 髋→肩 的夹角
        hip_left.append(_vector_angle_deg(lk - lh, ls - lh))
        hip_right.append(_vector_angle_deg(rk - rh, rs - rh))

        # 膝关节角: 膝→髋 与 膝→踝 的夹角
        knee_left.append(_vector_angle_deg(lh - lk, la - lk))
        knee_right.append(_vector_angle_deg(rh - rk, ra - rk))

        # 踝屈伸角: 踝→膝 与 足跟→足尖 的夹角
        ankle_left.append(_vector_angle_deg(lk - la, ltoe - lheel))
        ankle_right.append(_vector_angle_deg(rk - ra, rtoe - rheel))

        # 小腿侧向倾斜角: 小腿(膝→踝) 与 地面法线(0,0,1) 的夹角
        v_shank_l = la - lk  # 膝→踝 (注意方向)
        v_shank_r = ra - rk
        v_ground = np.array([0.0, 0.0, 1.0])
        shank_tilt_left.append(_vector_angle_deg(v_shank_l, v_ground))
        shank_tilt_right.append(_vector_angle_deg(v_shank_r, v_ground))

        # 躯干法向量（双肩中点 → 双髋中点，近似躯干方向）
        shoulder_mid = (ls + rs) / 2.0
        hip_mid = (lh + rh) / 2.0
        trunk_vec = shoulder_mid - hip_mid
        trunk_tilt.append(trunk_vec)

    df["left_hip_angle_deg"] = hip_left
    df["right_hip_angle_deg"] = hip_right
    df["left_knee_angle_deg"] = knee_left
    df["right_knee_angle_deg"] = knee_right
    df["left_ankle_angle_deg"] = ankle_left
    df["right_ankle_angle_deg"] = ankle_right
    df["left_shank_tilt_angle_deg"] = shank_tilt_left
    df["right_shank_tilt_angle_deg"] = shank_tilt_right

    # 躯干平面波动率：相邻帧躯干法向量夹角 / Δt
    _trunk_angles = []
    for i in range(len(trunk_tilt)):
        if i == 0:
            _trunk_angles.append(0.0)
        else:
            _trunk_angles.append(_vector_angle_deg(trunk_tilt[i], trunk_tilt[i - 1]))
    df["trunk_tilt_angle_delta_deg"] = _trunk_angles
    df["trunk_tilt_rate_deg_s"] = df["trunk_tilt_angle_delta_deg"] / dt if dt > 0 else 0.0

    # ============================
    # 7. 关节角速度 & 角加速度
    # ============================
    angle_cols = [
        "left_hip_angle_deg", "right_hip_angle_deg",
        "left_knee_angle_deg", "right_knee_angle_deg",
        "left_ankle_angle_deg", "right_ankle_angle_deg",
    ]
    for angle_col in angle_cols:
        vel_col = angle_col.replace("_angle_deg", "_angular_velocity_deg_s")
        acc_col = angle_col.replace("_angle_deg", "_angular_acceleration_deg_s2")
        df[vel_col] = _derivative(df[angle_col], dt)
        df[acc_col] = _derivative(df[vel_col], dt)

    # ============================
    # 8. 支撑 / 腾空状态（双阈值滞回）
    # ============================
    airborne_cfg = params.get("airborne", {})
    contact_th = float(airborne_cfg.get("contact_threshold_m", 0.020))
    airborne_th = float(airborne_cfg.get("airborne_threshold_m", 0.040))
    min_frames = int(airborne_cfg.get("min_consecutive_frames", 2))

    for side in ["left", "right"]:
        clearance_col = f"{side}_clearance_m"
        state_col = f"{side}_support_state"
        states = _apply_hysteresis(df[clearance_col], contact_th, airborne_th, min_frames)
        df[state_col] = states

    # 支撑模式
    def _support_mode(row):
        l = row["left_support_state"]
        r = row["right_support_state"]
        if l == "airborne" and r == "airborne":
            return "double_airborne"
        if l == "airborne":
            return "left_airborne"
        if r == "airborne":
            return "right_airborne"
        return "double_support"

    df["support_mode"] = df.apply(_support_mode, axis=1)

    # 落地事件
    df["left_landing_event"] = (
        df["left_support_state"].shift(1).eq("airborne")
        & df["left_support_state"].eq("support")
    ).fillna(False).astype(int)
    df["right_landing_event"] = (
        df["right_support_state"].shift(1).eq("airborne")
        & df["right_support_state"].eq("support")
    ).fillna(False).astype(int)
    df["step_event_count"] = df["left_landing_event"] + df["right_landing_event"]

    # ============================
    # 9. 标记列（后续切分使用）
    # ============================
    df["phase_label"] = "unassigned"
    df["segment_id"] = pd.NA
    df["cycle_id"] = pd.NA
    df["target_cell"] = pd.NA

    return df


def _apply_hysteresis(
    clearance_series: pd.Series,
    contact_th: float,
    airborne_th: float,
    min_frames: int,
) -> pd.Series:
    """双阈值滞回 + 连续帧稳定判定。"""
    if clearance_series.empty:
        return pd.Series(dtype="object")

    # 根据前几帧估算初始状态
    valid = clearance_series.dropna()
    if valid.empty:
        init_state = "support"
    else:
        init_state = "support" if float(valid.iloc[0]) < airborne_th else "airborne"

    states = []
    current_state = init_state
    pending_state = current_state
    pending_count = 0

    for val in clearance_series.tolist():
        if pd.isna(val):
            candidate = current_state
        elif float(val) <= contact_th:
            candidate = "support"
        elif float(val) >= airborne_th:
            candidate = "airborne"
        else:
            candidate = current_state

        if candidate == current_state:
            pending_state = current_state
            pending_count = 0
        else:
            if candidate == pending_state:
                pending_count += 1
            else:
                pending_state = candidate
                pending_count = 1
            if pending_count >= min_frames:
                current_state = pending_state
                pending_count = 0

        states.append(current_state)

    return pd.Series(states, index=clearance_series.index, dtype="object")
