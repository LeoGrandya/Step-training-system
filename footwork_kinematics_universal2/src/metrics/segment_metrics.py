# -*- coding: utf-8 -*-
"""
段级运动学指标计算。

对每个切分段（移动/还原/停止），计算：
- 位移：重心/左右脚踝的绝对距离、左右距离、前后距离
- 速度：各点合速度极值、平均速度
- 腾空：单脚/双脚悬空时间、平均高度、最大高度
- 关节：髋/膝/踝 ROM、缓冲极限、蹬伸极限、制动瞬间角度
- 小腿倾斜角极值
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


def _safe_num(v):
    try:
        if pd.isna(v):
            return np.nan
        return float(v)
    except (ValueError, TypeError):
        return np.nan


def _segment_df(frame_df: pd.DataFrame, seg: Dict) -> pd.DataFrame:
    """从逐帧表提取指定 segment 的切片。"""
    s = seg["start_idx"]
    e = seg["end_idx"]
    if s >= len(frame_df) or e >= len(frame_df) or e < s:
        return pd.DataFrame()
    return frame_df.iloc[s:e + 1].copy()


def _path_length_3d(df: pd.DataFrame, prefix: str) -> float:
    """三维累计弧长。"""
    cols = [f"{prefix}_x", f"{prefix}_y", f"{prefix}_z"]
    if not set(cols).issubset(df.columns) or len(df) < 2:
        return 0.0
    sub = df[cols].dropna()
    if len(sub) < 2:
        return 0.0
    dx = sub[f"{prefix}_x"].diff().fillna(0.0)
    dy = sub[f"{prefix}_y"].diff().fillna(0.0)
    dz = sub[f"{prefix}_z"].diff().fillna(0.0)
    return float((dx.pow(2) + dy.pow(2) + dz.pow(2)).pow(0.5).sum())


def _displacement_abs(df: pd.DataFrame, prefix: str) -> Dict[str, float]:
    """绝对跨度 Dx, Dy, 以及三维直线距离。"""
    cols = [f"{prefix}_x", f"{prefix}_y", f"{prefix}_z"]
    if not set(cols).issubset(df.columns) or df.empty:
        return {"dx": 0.0, "dy": 0.0, "dz": 0.0, "d3d": 0.0}
    sub = df[cols].dropna()
    if len(sub) < 2:
        return {"dx": 0.0, "dy": 0.0, "dz": 0.0, "d3d": 0.0}
    dx = abs(float(sub[f"{prefix}_x"].iloc[-1] - sub[f"{prefix}_x"].iloc[0]))
    dy = abs(float(sub[f"{prefix}_y"].iloc[-1] - sub[f"{prefix}_y"].iloc[0]))
    dz = abs(float(sub[f"{prefix}_z"].iloc[-1] - sub[f"{prefix}_z"].iloc[0]))
    d3d = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    return {"dx": dx, "dy": dy, "dz": dz, "d3d": d3d}


def _safe_mean(df: pd.DataFrame, col: str) -> Optional[float]:
    if col not in df.columns or df.empty:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return float(s.mean()) if not s.empty else None


def _safe_max(df: pd.DataFrame, col: str) -> Optional[float]:
    if col not in df.columns or df.empty:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return float(s.max()) if not s.empty else None


def _safe_min(df: pd.DataFrame, col: str) -> Optional[float]:
    if col not in df.columns or df.empty:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return float(s.min()) if not s.empty else None


def _airborne_events_in_segment(
    df: pd.DataFrame, params: dict, fps: float
) -> Dict[str, float]:
    """在一个段内统计腾空事件。"""
    airborne_cfg = params.get("airborne", {})
    single_min_h = float(airborne_cfg.get("single_airborne_min_height_m", 0.025))
    single_min_f = int(airborne_cfg.get("single_airborne_min_frames", 5))
    double_min_h = float(airborne_cfg.get("double_airborne_min_height_m", 0.020))
    double_min_f = int(airborne_cfg.get("double_airborne_min_frames", 5))

    result = {
        "left_airborne_time_s": 0.0, "left_airborne_avg_height_m": 0.0, "left_airborne_max_height_m": 0.0,
        "right_airborne_time_s": 0.0, "right_airborne_avg_height_m": 0.0, "right_airborne_max_height_m": 0.0,
        "double_airborne_time_s": 0.0, "double_airborne_avg_height_m": 0.0, "double_airborne_max_height_m": 0.0,
    }

    if df.empty:
        return result

    # 左脚单次腾空
    left_mask = df["left_clearance_m"] >= single_min_h
    left_runs = _extract_runs(left_mask, single_min_f)
    if left_runs:
        times, avgs, maxs = [], [], []
        for s, e in left_runs:
            sub = df.iloc[s:e + 1]
            times.append(len(sub) / fps)
            avgs.append(float(sub["left_clearance_m"].mean()))
            maxs.append(float(sub["left_clearance_m"].max()))
        result["left_airborne_time_s"] = sum(times)
        result["left_airborne_avg_height_m"] = float(np.mean(avgs)) if avgs else 0.0
        result["left_airborne_max_height_m"] = max(maxs) if maxs else 0.0

    # 右脚同理
    right_mask = df["right_clearance_m"] >= single_min_h
    right_runs = _extract_runs(right_mask, single_min_f)
    if right_runs:
        times, avgs, maxs = [], [], []
        for s, e in right_runs:
            sub = df.iloc[s:e + 1]
            times.append(len(sub) / fps)
            avgs.append(float(sub["right_clearance_m"].mean()))
            maxs.append(float(sub["right_clearance_m"].max()))
        result["right_airborne_time_s"] = sum(times)
        result["right_airborne_avg_height_m"] = float(np.mean(avgs)) if avgs else 0.0
        result["right_airborne_max_height_m"] = max(maxs) if maxs else 0.0

    # 双脚
    double_mask = (df["left_clearance_m"] >= double_min_h) & (df["right_clearance_m"] >= double_min_h)
    double_runs = _extract_runs(double_mask, double_min_f)
    if double_runs:
        times, avgs, maxs = [], [], []
        for s, e in double_runs:
            sub = df.iloc[s:e + 1]
            avg_h = float(sub[["left_clearance_m", "right_clearance_m"]].mean(axis=1).mean())
            max_h = float(sub[["left_clearance_m", "right_clearance_m"]].mean(axis=1).max())
            times.append(len(sub) / fps)
            avgs.append(avg_h)
            maxs.append(max_h)
        result["double_airborne_time_s"] = sum(times)
        result["double_airborne_avg_height_m"] = float(np.mean(avgs)) if avgs else 0.0
        result["double_airborne_max_height_m"] = max(maxs) if maxs else 0.0

    return result


def _extract_runs(bool_series: pd.Series, min_len: int) -> List[tuple]:
    """提取连续 True 段。"""
    runs = []
    vals = bool_series.fillna(False).astype(bool).tolist()
    start = None
    length = 0
    for i, v in enumerate(vals):
        if v:
            if start is None:
                start = i
            length += 1
        else:
            if start is not None and length >= min_len:
                runs.append((start, i - 1))
            start = None
            length = 0
    if start is not None and length >= min_len:
        runs.append((start, len(vals) - 1))
    return runs


def compute_segment_metrics(
    frame_df: pd.DataFrame,
    segments: List[Dict],
    pace_id: int,
    params: dict,
) -> pd.DataFrame:
    """
    对所有切分段逐段计算底层生物力学指标。

    Returns
    -------
    pd.DataFrame 每行一个段。
    """
    fps = float(params.get("fps", 60.0))
    dt = 1.0 / fps if fps > 0 else 0.0
    rows = []

    joint_cols = {
        "left_hip": "左髋",
        "right_hip": "右髋",
        "left_knee": "左膝",
        "right_knee": "右膝",
        "left_ankle": "左踝",
        "right_ankle": "右踝",
    }

    for seg in segments:
        seg_df = _segment_df(frame_df, seg)
        if seg_df.empty:
            continue

        # 耗时: 帧数 × Δt（与移动总耗时 ΣFrames/FPS 一致）
        duration_s = len(seg_df) * dt
        phase = seg.get("phase", "move")
        target_cell = seg.get("target_cell", None)
        from_cell = seg.get("from_cell", None)
        to_cell = seg.get("to_cell", None)

        # 段标签
        if phase == "pre_move_stop":
            label = f"第{target_cell}格第{seg.get('cycle_id','?')}次【移动前停止】"
        elif phase == "move":
            if pace_id in (4, 5, 6, 7, 8):
                label = f"第{seg.get('cycle_id','?')}次【{from_cell} → {to_cell}移动】"
            else:
                label = f"第{target_cell}格第{seg.get('cycle_id','?')}次【移动】"
        elif phase == "pre_restore_stop":
            label = f"第{target_cell}格第{seg.get('cycle_id','?')}次【还原前停止】"
        elif phase == "restore":
            label = f"第{target_cell}格第{seg.get('cycle_id','?')}次【还原】"
        else:
            label = f"第{seg.get('cycle_id','?')}次【{phase}】"

        row = {
            "时间段": label,
            "帧范围": f"{seg['start_frame']}-{seg['end_frame']}",
            "耗时_s": round(duration_s, 4),
            "segment_id": seg["segment_id"],
            "cycle_id": seg.get("cycle_id"),
            "phase": phase,
            "target_cell": target_cell,
            "from_cell": from_cell,
            "to_cell": to_cell,
        }

        # ---- 位移参数 ----
        for prefix, name in [("com", "重心"), ("left_ankle", "左脚踝"), ("right_ankle", "右脚踝")]:
            abs_dist = _path_length_3d(seg_df, prefix)
            disp = _displacement_abs(seg_df, prefix)
            row[f"{name}移动绝对距离_m"] = round(abs_dist, 4)
            row[f"{name}左右移动距离_m"] = round(disp["dx"], 4)
            row[f"{name}前后移动距离_m"] = round(disp["dy"], 4)

        # ---- 速度参数 ----
        for prefix, name in [("com", "重心"), ("left_ankle", "左脚踝"), ("right_ankle", "右脚踝")]:
            row[f"{name}合速度极值_mps"] = round(_safe_max(seg_df, f"{prefix}_speed_mps") or 0.0, 4)
            # 平均速度 = Dcom / T (文档公式), 非 mean(逐帧速度)
            abs_d = _path_length_3d(seg_df, prefix)
            row[f"{name}平均速度_mps"] = round(abs_d / duration_s, 4) if duration_s > 0 else 0.0

        # ---- 腾空参数 ----
        airborne = _airborne_events_in_segment(seg_df, params, fps)
        for k, v in airborne.items():
            row[k] = round(v, 4)

        # ---- 关节参数 ----
        for joint_key, joint_name in joint_cols.items():
            angle_col = f"{joint_key}_angle_deg"
            vel_col = f"{joint_key}_angular_velocity_deg_s"
            acc_col = f"{joint_key}_angular_acceleration_deg_s2"

            max_angle = _safe_max(seg_df, angle_col)
            min_angle = _safe_min(seg_df, angle_col)
            rom = (max_angle - min_angle) if max_angle is not None and min_angle is not None else None

            row[f"{joint_name}ROM_deg"] = round(rom, 2) if rom is not None else None
            row[f"{joint_name}缓冲极限_deg"] = round(min_angle, 2) if min_angle is not None else None
            row[f"{joint_name}蹬伸极限_deg"] = round(max_angle, 2) if max_angle is not None else None
            row[f"{joint_name}角速度极值_deg_s"] = round(_safe_max(seg_df, vel_col) or 0.0, 2)
            row[f"{joint_name}角加速度极值_deg_s2"] = round(_safe_max(seg_df, acc_col) or 0.0, 2)

            # 制动变向瞬间角度（移动段取最后一帧，还原段取最后一帧做 Impact Angle）
            if phase in ("move", "restore"):
                last_val = seg_df[angle_col].dropna()
                if not last_val.empty:
                    row[f"{joint_name}制动瞬间角度_deg"] = round(float(last_val.iloc[-1]), 2)

        # ---- 小腿倾斜角 ----
        for side in ["left", "right"]:
            col = f"{side}_shank_tilt_angle_deg"
            name = "左小腿" if side == "left" else "右小腿"
            row[f"{name}倾斜角极值_deg"] = round(_safe_max(seg_df, col) or 0.0, 2)
            row[f"{name}倾斜角均值_deg"] = round(_safe_mean(seg_df, col) or 0.0, 2)

        rows.append(row)

    return pd.DataFrame(rows)
