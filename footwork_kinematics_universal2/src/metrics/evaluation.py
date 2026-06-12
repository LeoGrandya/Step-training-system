# -*- coding: utf-8 -*-
"""
评价参数计算模块。

包含：
- 变向衔接时间 (Turning Transition Time)
- 小腿侧向倾斜角 (Shank Tilt Angle) ← 逐帧已算，此处只取极值
- 屈膝锁关节指数 KLI (%)
- 支撑期双脚重叠度 DSO (%)
- 人体动态包络线面积 AreaEnvelope (m²) 与翼展比 DAR
- 步伐发力效率 bq (%)
- 步幅/耗能比 Stride-to-Energy Ratio (m/J)
- 质心起伏经济性轨迹平滑度 Smoothness (m/J)
- 时序一致性归一化 DTW 距离
- 各关节做功与能耗占比 (%)
- 躯干平面波动率 Tilt_Rate (°/s)
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from scipy.spatial import ConvexHull

GRAVITY_ACC = 9.81


# ============================================================================
# 1. 变向衔接时间
# ============================================================================

def compute_transition_time(
    frame_df: pd.DataFrame,
    segments: List[Dict],
    transition_vel_threshold: float = 0.3,
    fps: float = 60.0,
) -> List[Dict]:
    """
    在每个移动段到达空间位移极点时，捕捉重心速度跌破阈值期间的
    低速过渡停顿时间。

    Returns
    -------
    List[Dict] 每个段一个 transition 记录。
    """
    results = []
    dt = 1.0 / fps if fps > 0 else 0.0

    for seg in segments:
        if seg.get("phase") != "move":
            continue
        s = seg["start_idx"]
        e = seg["end_idx"]
        seg_speeds = frame_df.iloc[s:e + 1]["com_speed_mps"]

        # 找到速度跌破阈值的连续区间
        low_speed_mask = seg_speeds <= transition_vel_threshold
        runs = _extract_boolean_runs(low_speed_mask)

        # 取末端（刹车点附近）的低速段
        if runs:
            last_run = runs[-1]
            duration = (last_run[1] - last_run[0] + 1) * dt
        else:
            duration = 0.0

        results.append({
            "segment_id": seg["segment_id"],
            "transition_time_s": round(duration, 4),
        })

    return results


# ============================================================================
# 2. 屈膝锁关节指数 KLI
# ============================================================================

def compute_kli(
    frame_df: pd.DataFrame,
    segments: List[Dict],
    knee_locking_angle_thr: float = 175.0,
) -> List[Dict]:
    """
    监控每个移动段内膝关节角度 ≥ 阈值的帧占比。

    KLI = (锁定帧数 / 总帧数) × 100%
    """
    results = []
    for seg in segments:
        phase = seg.get("phase", "")
        if phase not in ("move", "restore"):
            continue
        s = seg["start_idx"]
        e = seg["end_idx"]
        seg_df = frame_df.iloc[s:e + 1]

        for side, col in [("left", "left_knee_angle_deg"), ("right", "right_knee_angle_deg")]:
            if col not in seg_df.columns:
                continue
            total = len(seg_df)
            locked = int((seg_df[col] >= knee_locking_angle_thr).fillna(False).sum())
            kli = (locked / total * 100.0) if total > 0 else 0.0

            results.append({
                "segment_id": seg["segment_id"],
                "side": side,
                "kli_pct": round(kli, 2),
            })

    return results


# ============================================================================
# 3. 支撑期双脚重叠度 DSO
# ============================================================================

def compute_dso(frame_df: pd.DataFrame) -> pd.Series:
    """
    逐帧计算 DSO。

    DSO = (1 - 2·DCoM-mid / Dstride) × 100%

    Dstride = 双踝水平距离
    DCoM-mid = COM 到双踝中点的水平距离
    """
    dso_values = []

    for _, row in frame_df.iterrows():
        la_x = _safe_float(row.get("left_ankle_x"))
        la_y = _safe_float(row.get("left_ankle_y"))
        ra_x = _safe_float(row.get("right_ankle_x"))
        ra_y = _safe_float(row.get("right_ankle_y"))
        com_x = _safe_float(row.get("com_x"))
        com_y = _safe_float(row.get("com_y"))

        if any(np.isnan(v) for v in [la_x, la_y, ra_x, ra_y, com_x, com_y]):
            dso_values.append(np.nan)
            continue

        d_stride = math.sqrt((la_x - ra_x) ** 2 + (la_y - ra_y) ** 2)
        mid_x = (la_x + ra_x) / 2.0
        mid_y = (la_y + ra_y) / 2.0
        d_com_mid = math.sqrt((com_x - mid_x) ** 2 + (com_y - mid_y) ** 2)

        if d_stride < 1e-6:
            dso_values.append(100.0)
        else:
            dso = (1.0 - 2.0 * d_com_mid / d_stride) * 100.0
            dso_values.append(dso)

    return pd.Series(dso_values, index=frame_df.index, dtype=float)


# ============================================================================
# 4. 人体动态包络线面积 & 翼展比
# ============================================================================

def compute_envelope_dar(frame_df: pd.DataFrame) -> pd.DataFrame:
    """
    逐帧计算凸包面积和翼展比。

    边缘点：COM + 左右肩/髋/膝/踝/足跟/足尖的 (x, z) 投影。
    AreaEnvelope 使用 Shoelace 公式。
    DAR = (xmax - xmin) / (zmax - zmin)
    """
    edge_joints = [
        "com",
        "left_shoulder", "right_shoulder",
        "left_hip", "right_hip",
        "left_knee", "right_knee",
        "left_ankle", "right_ankle",
        "left_heel", "right_heel",
        "left_foot_index", "right_foot_index",
    ]

    areas = []
    dars = []

    for _, row in frame_df.iterrows():
        points = []
        for joint in edge_joints:
            x = _safe_float(row.get(f"{joint}_x"))
            z = _safe_float(row.get(f"{joint}_z"))
            if not np.isnan(x) and not np.isnan(z):
                points.append([x, z])

        if len(points) < 3:
            areas.append(np.nan)
            dars.append(np.nan)
            continue

        pts = np.array(points)
        try:
            hull = ConvexHull(pts)
            area = float(hull.volume)  # 2D 中 = 面积
        except Exception:
            # 退化为 shoelace
            area = 0.0
            k = len(pts)
            for i in range(k):
                j = (i + 1) % k
                area += pts[i, 0] * pts[j, 1] - pts[j, 0] * pts[i, 1]
            area = abs(area) / 2.0

        x_range = float(pts[:, 0].max() - pts[:, 0].min())
        z_range = float(pts[:, 1].max() - pts[:, 1].min())
        dar = x_range / z_range if z_range > 1e-6 else np.nan

        areas.append(area)
        dars.append(dar)

    result = pd.DataFrame({
        "envelope_area_m2": areas,
        "envelope_dar": dars,
    }, index=frame_df.index)
    return result


# ============================================================================
# 5. 步伐发力效率 bq
# ============================================================================

def compute_efficiency_bq(
    frame_df: pd.DataFrame,
    segments: List[Dict],
    body_weight_kg: float,
) -> List[Dict]:
    """
    bq = (体重 × 重力加速度 × 水平累计位移) / 下肢关节总做功 × 100%

    水平累计位移 c = Σ|Δx| + Σ|Δy| (时序积分)
    总做功 bp = Σ|P(t)|·Δt, P(t) = τ(t)·ω(t)
    """
    results = []
    fps_est = 60.0

    for seg in segments:
        phase = seg.get("phase", "")
        if phase not in ("move", "restore"):
            continue
        s = seg["start_idx"]
        e = seg["end_idx"]
        seg_df = frame_df.iloc[s:e + 1].copy()
        if seg_df.empty:
            continue

        # 水平累计位移
        dx = seg_df["com_x"].diff().abs().fillna(0.0)
        dy = seg_df["com_y"].diff().abs().fillna(0.0)
        c_horizontal = float(dx.sum() + dy.sum())

        # 各关节总做功
        total_work_j = 0.0
        for side in ["left", "right"]:
            for joint in ["hip", "knee"]:
                torque_col = f"{side}_{joint}_torque_nm"
                vel_col = f"{side}_{joint}_angular_velocity_deg_s"
                if torque_col in seg_df.columns and vel_col in seg_df.columns:
                    # τ 和 ω 可能不同符号（向心/离心），取绝对值
                    power = (seg_df[torque_col].abs() * seg_df[vel_col].abs() * (math.pi / 180.0))
                    total_work_j += float(power.sum() / fps_est)

        if total_work_j > 0:
            bq = (body_weight_kg * GRAVITY_ACC * c_horizontal) / total_work_j * 100.0
        else:
            bq = np.nan

        results.append({
            "segment_id": seg["segment_id"],
            "efficiency_bq_pct": round(bq, 2) if not np.isnan(bq) else None,
        })

    return results


# ============================================================================
# 6. 步幅/耗能比
# ============================================================================

def compute_stride_to_energy(
    frame_df: pd.DataFrame,
    segments: List[Dict],
) -> List[Dict]:
    """
    Stride-to-Energy Ratio = SL / bp  (m/J)

    SL = 移动段起点到终点的绝对水平空间跨度 (m)
    bp = Σ|τ(t)·ω(t)|·Δt 各下肢关节总做功 (J)
    """
    fps_est = 60.0
    dt = 1.0 / fps_est
    results = []

    for seg in segments:
        phase = seg.get("phase", "")
        if phase not in ("move", "restore"):
            continue
        sid = seg["segment_id"]
        s = seg["start_idx"]
        e = seg["end_idx"]
        seg_df = frame_df.iloc[s:e + 1]

        # SL: 水平空间跨度
        if not seg_df.empty and len(seg_df) >= 2:
            dx = float(seg_df["com_x"].iloc[-1] - seg_df["com_x"].iloc[0])
            dy = float(seg_df["com_y"].iloc[-1] - seg_df["com_y"].iloc[0])
            SL = (dx ** 2 + dy ** 2) ** 0.5
        else:
            SL = 0.0

        # bp: 各关节总做功
        total_work = 0.0
        for side in ["left", "right"]:
            for joint in ["hip", "knee", "ankle"]:
                t_col = f"{side}_{joint}_torque_nm"
                v_col = f"{side}_{joint}_angular_velocity_deg_s"
                if t_col in seg_df.columns and v_col in seg_df.columns:
                    power = (seg_df[t_col].abs() * seg_df[v_col].abs() * (math.pi / 180.0))
                    total_work += float(power.sum() * dt)

        ratio = (SL / total_work) if total_work > 0 else None
        results.append({
            "segment_id": sid,
            "stride_to_energy_ratio_mJ": round(ratio, 6) if ratio is not None else None,
        })

    return results


# ============================================================================
# 7. 质心起伏经济性轨迹平滑度
# ============================================================================

def compute_trajectory_smoothness(
    frame_df: pd.DataFrame,
    segments: List[Dict],
    body_weight_kg: float,
) -> List[Dict]:
    """
    Smoothness = 水平位移 / 垂直能耗

    ΔEz = mass·g·|Δz| + 0.5·mass·|Δ(vz²)|
    Smoothness = Σ√(Δx²+Δy²) / ΔEz
    """
    results = []
    fps_est = 60.0

    for seg in segments:
        phase = seg.get("phase", "")
        if phase not in ("move", "restore"):
            continue
        s = seg["start_idx"]
        e = seg["end_idx"]
        seg_df = frame_df.iloc[s:e + 1].copy()
        if seg_df.empty or len(seg_df) < 2:
            continue

        # 水平位移累计
        dx = seg_df["com_x"].diff().fillna(0.0)
        dy = seg_df["com_y"].diff().fillna(0.0)
        horizontal_step = (dx.pow(2) + dy.pow(2)).pow(0.5)
        total_horizontal = float(horizontal_step.sum())

        # 垂直能耗
        dz = seg_df["com_z"].diff().fillna(0.0)
        vz_sq = seg_df["com_vz_mps"].pow(2) if "com_vz_mps" in seg_df.columns else pd.Series(0.0, index=seg_df.index)
        dvz_sq = vz_sq.diff().fillna(0.0)

        potential_energy = body_weight_kg * GRAVITY_ACC * dz.abs()
        kinetic_energy_vertical = 0.5 * body_weight_kg * dvz_sq.abs()
        delta_ez = float((potential_energy + kinetic_energy_vertical).sum())

        if delta_ez > 0:
            smoothness = total_horizontal / delta_ez
        else:
            smoothness = np.nan

        results.append({
            "segment_id": seg["segment_id"],
            "trajectory_smoothness_mJ": round(smoothness, 6) if not np.isnan(smoothness) else None,
        })

    return results


# ============================================================================
# 8. 归一化 DTW 距离
# ============================================================================

def compute_normalized_dtw(
    frame_df: pd.DataFrame,
    segments: List[Dict],
    normalized_length: int = 100,
) -> float:
    """
    将所有同类型的移动段的速度曲线归一化到 N 帧，
    计算 DTW 距离，取均值作为一致性指标。

    若无外部专家模板，则用各段均值曲线作为参考模板。
    """
    move_segments = [s for s in segments if s.get("phase") == "move"]
    if len(move_segments) < 2:
        return 0.0

    # 提取所有移动段的速度曲线，三次样条插值到 N 帧
    from scipy.interpolate import CubicSpline

    curves = []
    for seg in move_segments:
        s = seg["start_idx"]
        e = seg["end_idx"]
        seg_df = frame_df.iloc[s:e + 1]
        speeds = seg_df["com_speed_mps"].dropna().to_numpy(dtype=float)
        if len(speeds) < 5:
            continue

        x_orig = np.linspace(0, 1, len(speeds))
        x_new = np.linspace(0, 1, normalized_length)
        try:
            cs = CubicSpline(x_orig, speeds)
            curve = cs(x_new)
            curves.append(curve)
        except Exception:
            continue

    if len(curves) < 2:
        return 0.0

    # 参考模板：所有曲线的均值
    template = np.mean(np.array(curves), axis=0)

    # 计算每条曲线与模板的 DTW 距离
    dtw_distances = []
    for curve in curves:
        d = _dtw_distance(curve, template)
        dtw_distances.append(d)

    mean_dtw = float(np.mean(dtw_distances)) if dtw_distances else 0.0
    # 归一化：除以路径长度 N
    normalized_dtw = mean_dtw / normalized_length
    return round(normalized_dtw, 6)


def _dtw_distance(x: np.ndarray, y: np.ndarray) -> float:
    """两个等长序列的 DTW 距离。"""
    n = len(x)
    d = np.zeros((n, n))
    d[0, 0] = abs(x[0] - y[0])
    for i in range(1, n):
        d[i, 0] = d[i - 1, 0] + abs(x[i] - y[0])
    for j in range(1, n):
        d[0, j] = d[0, j - 1] + abs(x[0] - y[j])
    for i in range(1, n):
        for j in range(1, n):
            cost = abs(x[i] - y[j])
            d[i, j] = cost + min(d[i - 1, j], d[i, j - 1], d[i - 1, j - 1])
    return float(d[n - 1, n - 1])


# ============================================================================
# 9. 各关节做功与能耗占比
# ============================================================================

def compute_joint_work_ratio(
    frame_df: pd.DataFrame,
    segments: List[Dict],
) -> List[Dict]:
    """
    在每个移动段内，计算 W_hip, W_knee, W_ankle 各自的占比。

    W_joint = Σ|τ_joint(t) · ω_joint(t)| · Δt
    占比 = W_joint / (W_hip + W_knee + W_ankle) × 100%
    """
    results = []
    fps_est = 60.0
    dt = 1.0 / fps_est

    for seg in segments:
        phase = seg.get("phase", "")
        if phase not in ("move", "restore"):
            continue
        s = seg["start_idx"]
        e = seg["end_idx"]
        seg_df = frame_df.iloc[s:e + 1]

        side_work = {}
        for side in ["left", "right"]:
            work_joints = {}
            for joint in ["hip", "knee", "ankle"]:
                torque_col = f"{side}_{joint}_torque_nm"
                vel_col = f"{side}_{joint}_angular_velocity_deg_s"
                if torque_col in seg_df.columns and vel_col in seg_df.columns:
                    power = seg_df[torque_col].abs() * seg_df[vel_col].abs() * (math.pi / 180.0)
                    work = float(power.sum() * dt)
                else:
                    work = 0.0
                work_joints[joint] = work

            total = sum(work_joints.values())
            if total > 0:
                ratios = {j: (w / total * 100.0) for j, w in work_joints.items()}
            else:
                ratios = {j: 0.0 for j in work_joints}

            side_work[side] = {
                "total_work_j": total,
                "hip_pct": round(ratios["hip"], 2),
                "knee_pct": round(ratios["knee"], 2),
                "ankle_pct": round(ratios["ankle"], 2),
            }

        results.append({
            "segment_id": seg["segment_id"],
            "left_hip_work_pct": side_work["left"]["hip_pct"],
            "left_knee_work_pct": side_work["left"]["knee_pct"],
            "left_ankle_work_pct": side_work["left"]["ankle_pct"],
            "right_hip_work_pct": side_work["right"]["hip_pct"],
            "right_knee_work_pct": side_work["right"]["knee_pct"],
            "right_ankle_work_pct": side_work["right"]["ankle_pct"],
        })

    return results


# ============================================================================
# 辅助
# ============================================================================

def _safe_float(v) -> float:
    try:
        if pd.isna(v):
            return np.nan
        return float(v)
    except (ValueError, TypeError):
        return np.nan


def _extract_boolean_runs(series: pd.Series) -> List[Tuple[int, int]]:
    """提取连续 True 的 (start, end) 索引。"""
    vals = series.fillna(False).astype(bool).tolist()
    runs = []
    start = None
    for i, v in enumerate(vals):
        if v:
            if start is None:
                start = i
        else:
            if start is not None:
                runs.append((start, i - 1))
                start = None
    if start is not None:
        runs.append((start, len(vals) - 1))
    return runs


def compute_torque_power(frame_df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    简化逆动力学：计算髋/膝关节力矩与功率。

    使用身高体重估算环节参数。
    """
    body = params.get("body", {})
    height_m = float(body.get("height_m", 1.65))
    weight_kg = float(body.get("weight_kg", 55.0))
    fps = float(params.get("fps", 60.0))
    dt = 1.0 / fps if fps > 0 else 0.0

    df = frame_df.copy()

    # 环节参数估算
    thigh_mass = weight_kg * 0.10   # 单侧大腿质量
    shank_mass = weight_kg * 0.06   # 单侧小腿质量
    foot_mass = weight_kg * 0.03    # 单侧足质量
    thigh_length = height_m * 0.23
    shank_length = height_m * 0.21
    thigh_com_dist = thigh_length * 0.45
    shank_com_dist = shank_length * 0.43
    thigh_I = thigh_mass * (thigh_com_dist ** 2)
    shank_I = shank_mass * (shank_com_dist ** 2)

    for side in ["left", "right"]:
        # 关节角加速度 (rad/s²)
        hip_acc = np.deg2rad(df[f"{side}_hip_angular_acceleration_deg_s2"])
        knee_acc = np.deg2rad(df[f"{side}_knee_angular_acceleration_deg_s2"])
        ankle_acc = np.deg2rad(df[f"{side}_ankle_angular_acceleration_deg_s2"])

        # 关节角速度 (rad/s)
        hip_vel = np.deg2rad(df[f"{side}_hip_angular_velocity_deg_s"])
        knee_vel = np.deg2rad(df[f"{side}_knee_angular_velocity_deg_s"])
        ankle_vel = np.deg2rad(df[f"{side}_ankle_angular_velocity_deg_s"])

        # 简化力矩 = I × α (忽略重力项和交互力矩)
        df[f"{side}_hip_torque_nm"] = thigh_I * hip_acc
        df[f"{side}_knee_torque_nm"] = shank_I * knee_acc
        df[f"{side}_ankle_torque_nm"] = shank_I * 0.3 * ankle_acc  # 踝关节惯量更小

        # 功率 = τ × ω
        df[f"{side}_hip_power_w"] = df[f"{side}_hip_torque_nm"] * hip_vel
        df[f"{side}_knee_power_w"] = df[f"{side}_knee_torque_nm"] * knee_vel
        df[f"{side}_ankle_power_w"] = df[f"{side}_ankle_torque_nm"] * ankle_vel

    return df
