# -*- coding: utf-8 -*-
"""运行时必需。运动学主流程：读 pose3d CSV、切分步伐单元、算指标并导出图表 JSON；由 web_1 kinematics_service 调用。"""
from __future__ import annotations

import math
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import warnings
from pandas.errors import PerformanceWarning

warnings.filterwarnings("ignore", category=PerformanceWarning)


# -----------------------------
# 字体
# -----------------------------
def _set_chinese_font():
    """尽量兼容 Windows / Linux 的中文显示。"""
    font_candidates = [
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    family_names = [
        "Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC",
        "WenQuanYi Zen Hei", "Arial Unicode MS", "DejaVu Sans",
    ]

    selected_family = None
    for path in font_candidates:
        try:
            if Path(path).exists():
                fm.fontManager.addfont(path)
                selected_family = fm.FontProperties(fname=path).get_name()
                break
        except Exception:
            continue

    font_list = []
    if selected_family:
        font_list.append(selected_family)
    font_list.extend(family_names)

    plt.rcParams["font.sans-serif"] = font_list
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False


# -----------------------------
# 基础工具
# -----------------------------
def _safe_num(v):
    try:
        if pd.isna(v):
            return np.nan
        return float(v)
    except Exception:
        return np.nan


def _merge_joint_xyz(frame_df: pd.DataFrame, long_df: pd.DataFrame, joint_name: str) -> pd.DataFrame:
    sub = long_df[long_df["joint_name"] == joint_name][["frame_id", "x", "y", "z"]].copy()
    sub = sub.rename(columns={"x": f"{joint_name}_x", "y": f"{joint_name}_y", "z": f"{joint_name}_z"})
    return frame_df.merge(sub, on="frame_id", how="left")


def _estimate_ground_z(long_df: pd.DataFrame, fallback: float = 0.0) -> float:
    foot_joints = ["left_heel", "right_heel", "left_ankle", "right_ankle", "left_foot_index", "right_foot_index"]
    foot_df = long_df[long_df["joint_name"].isin(foot_joints)].copy()
    z = pd.to_numeric(foot_df["z"], errors="coerce").dropna()
    if z.empty:
        return float(fallback)
    return float(np.percentile(z.to_numpy(), 5))


def _estimate_center_xy(
    frame_df: pd.DataFrame,
    n_head: int = 60,
    mode: str = "head_mean",
) -> Tuple[float, float]:
    valid = frame_df[["com_x", "com_y"]].dropna()
    if valid.empty:
        return (0.0, 0.0)

    mode = str(mode or "head_mean").strip().lower()
    if mode == "robust_quantile":
        return (float(valid["com_x"].median()), float(valid["com_y"].median()))

    if mode == "static_window":
        speed_col = "com_horizontal_speed_mps" if "com_horizontal_speed_mps" in frame_df.columns else "com_speed_mps"
        speed = pd.to_numeric(frame_df.get(speed_col, pd.Series(dtype=float)), errors="coerce")
        speed = speed.replace([np.inf, -np.inf], np.nan)
        if not speed.dropna().empty:
            q = float(speed.quantile(0.35))
            still = frame_df.loc[speed <= q, ["com_x", "com_y"]].dropna()
            if len(still) >= 10:
                return (float(still["com_x"].median()), float(still["com_y"].median()))

    sub = valid.head(n_head)
    return (float(sub["com_x"].mean()), float(sub["com_y"].mean()))


def _locate_nine_grid_cell(x, y, center_xy, cell_size=0.9, total_size=2.7):
    cx, cy = center_xy
    half = total_size / 2.0
    x_min = cx - half
    y_min = cy - half

    if not (x_min <= x <= x_min + total_size and y_min <= y <= y_min + total_size):
        return np.nan

    col = int((x - x_min) // cell_size)
    row_from_bottom = int((y - y_min) // cell_size)

    if col < 0 or col > 2 or row_from_bottom < 0 or row_from_bottom > 2:
        return np.nan

    # 保持与原项目九宫格编号习惯一致：从上到下、从右到左编号
    col = 2 - col
    row_from_top = 2 - row_from_bottom
    return int(row_from_top * 3 + col + 1)


def _locate_nine_grid_cell_series(
    x: pd.Series,
    y: pd.Series,
    center_xy: tuple[float, float],
    cell_size: float = 0.9,
    total_size: float = 2.7,
) -> pd.Series:
    cx, cy = center_xy
    half = total_size / 2.0
    x_min = cx - half
    y_min = cy - half
    x_num = pd.to_numeric(x, errors="coerce")
    y_num = pd.to_numeric(y, errors="coerce")
    in_bounds = (
        x_num.ge(x_min)
        & x_num.le(x_min + total_size)
        & y_num.ge(y_min)
        & y_num.le(y_min + total_size)
    )
    col = np.floor((x_num - x_min) / cell_size).astype("Float64")
    row_from_bottom = np.floor((y_num - y_min) / cell_size).astype("Float64")
    valid_idx = (
        in_bounds
        & col.ge(0)
        & col.le(2)
        & row_from_bottom.ge(0)
        & row_from_bottom.le(2)
    )
    out = pd.Series(np.nan, index=x.index, dtype="Float64")
    if valid_idx.any():
        col_valid = (2 - col[valid_idx]).astype(int)
        row_top_valid = (2 - row_from_bottom[valid_idx]).astype(int)
        out.loc[valid_idx] = (row_top_valid * 3 + col_valid + 1).astype(float)
    return out


def _vector_angle_deg(v1: np.ndarray, v2: np.ndarray) -> float:
    if v1 is None or v2 is None:
        return np.nan
    if not np.isfinite(v1).all() or not np.isfinite(v2).all():
        return np.nan
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return np.nan
    cos_val = np.dot(v1, v2) / (n1 * n2)
    cos_val = np.clip(cos_val, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_val)))


def _signed_sagittal_ankle_angle_deg(knee_y, knee_z, ankle_y, ankle_z, toe_y, toe_z) -> float:
    shank = np.array([knee_y - ankle_y, knee_z - ankle_z], dtype=float)
    foot = np.array([toe_y - ankle_y, toe_z - ankle_z], dtype=float)
    if not np.isfinite(shank).all() or not np.isfinite(foot).all():
        return np.nan
    n1 = np.linalg.norm(shank)
    n2 = np.linalg.norm(foot)
    if n1 == 0 or n2 == 0:
        return np.nan
    cos_val = np.dot(shank, foot) / (n1 * n2)
    cos_val = np.clip(cos_val, -1.0, 1.0)
    angle = np.degrees(np.arccos(cos_val))
    return float(90.0 - angle)


def _derivative(series: pd.Series, dt: float) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().empty or dt <= 0:
        return pd.Series(np.zeros(len(s)), index=s.index, dtype=float)
    arr = s.interpolate(limit_direction="both").to_numpy(dtype=float)
    der = np.gradient(arr, dt)
    return pd.Series(der, index=s.index, dtype=float)


def _consecutive_lengths(values: List[object]) -> List[int]:
    def _safe_truthy(x: object) -> bool:
        if x is None or x is pd.NA:
            return False
        if isinstance(x, (bool, np.bool_)):
            return bool(x)
        if isinstance(x, (int, np.integer)):
            return int(x) != 0
        if isinstance(x, (float, np.floating)):
            return (not np.isnan(float(x))) and float(x) != 0.0
        if isinstance(x, str):
            return x != ""
        return False

    out = []
    last = object()
    count = 0
    for v in values:
        v_missing = _safe_truthy(pd.isna(v))
        last_missing = _safe_truthy(pd.isna(last))
        same = False
        if v_missing and last_missing:
            same = True
        elif (not v_missing) and (not last_missing):
            same = _safe_truthy(v == last)
        if same:
            count += 1
        else:
            count = 1
            last = v
        out.append(count)
    return out


def _first_run_start(bool_series: pd.Series, start_idx: int, min_len: int) -> Optional[int]:
    vals = bool_series.fillna(False).astype(bool).tolist()
    run = 0
    for i in range(start_idx, len(vals)):
        if vals[i]:
            run += 1
            if run >= min_len:
                return i - min_len + 1
        else:
            run = 0
    return None


def _first_run_end(bool_series: pd.Series, start_idx: int, min_len: int) -> Optional[int]:
    vals = bool_series.fillna(False).astype(bool).tolist()
    run = 0
    for i in range(start_idx, len(vals)):
        if vals[i]:
            run += 1
            if run >= min_len:
                return i
        else:
            run = 0
    return None


def _count_runs(bool_series: pd.Series, min_len: int = 1) -> int:
    count = 0
    run = 0
    for v in bool_series.fillna(False).astype(bool).tolist():
        if v:
            run += 1
        else:
            if run >= min_len:
                count += 1
            run = 0
    if run >= min_len:
        count += 1
    return count


def _extract_runs(bool_series: pd.Series, min_len: int) -> List[Tuple[int, int]]:
    runs = []
    run_start = None
    run_len = 0
    vals = bool_series.fillna(False).astype(bool).tolist()
    for i, v in enumerate(vals):
        if v:
            if run_start is None:
                run_start = i
            run_len += 1
        else:
            if run_start is not None and run_len >= min_len:
                runs.append((run_start, i - 1))
            run_start = None
            run_len = 0
    if run_start is not None and run_len >= min_len:
        runs.append((run_start, len(vals) - 1))
    return runs


def _distance_2d(x1, y1, x2, y2):
    if any(pd.isna(v) for v in [x1, y1, x2, y2]):
        return np.nan
    return float(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))


def _distance_3d(x1, y1, z1, x2, y2, z2):
    if any(pd.isna(v) for v in [x1, y1, z1, x2, y2, z2]):
        return np.nan
    return float(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2))


def _path_stats(segment_df: pd.DataFrame, prefix: str) -> Dict[str, float]:
    need = [f"{prefix}_x", f"{prefix}_y", f"{prefix}_z"]
    if not set(need).issubset(segment_df.columns) or segment_df.empty:
        return {
            "abs_distance_m": np.nan,
            "left_right_distance_m": np.nan,
            "front_back_distance_m": np.nan,
        }
    sub = segment_df[need].dropna()
    if len(sub) < 2:
        return {
            "abs_distance_m": 0.0,
            "left_right_distance_m": 0.0,
            "front_back_distance_m": 0.0,
        }
    dx = sub[f"{prefix}_x"].diff().fillna(0.0)
    dy = sub[f"{prefix}_y"].diff().fillna(0.0)
    dz = sub[f"{prefix}_z"].diff().fillna(0.0)
    abs_dist = np.sqrt(dx.pow(2) + dy.pow(2) + dz.pow(2)).sum()
    lr = dx.abs().sum()
    fb = dy.abs().sum()
    return {
        "abs_distance_m": float(abs_dist),
        "left_right_distance_m": float(lr),
        "front_back_distance_m": float(fb),
    }


def _mean_or_nan(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns or df.empty:
        return np.nan
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return np.nan
    return float(s.mean())


def _max_or_nan(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns or df.empty:
        return np.nan
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return np.nan
    return float(s.max())


def _min_or_nan(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns or df.empty:
        return np.nan
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return np.nan
    return float(s.min())


def _abs_mean_or_nan(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns or df.empty:
        return np.nan
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return np.nan
    return float(s.abs().mean())


def _abs_max_or_nan(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns or df.empty:
        return np.nan
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return np.nan
    return float(s.abs().max())


def _duration_s(segment_df: pd.DataFrame, fps: float) -> float:
    if segment_df.empty:
        return 0.0
    return float(len(segment_df) / fps)


def _segment_summary(frame_df: pd.DataFrame, start_idx: int, end_idx: int, fps: float, stage_name: str, cycle_id: int, target_cell: int) -> Dict[str, object]:
    if start_idx is None or end_idx is None or end_idx < start_idx:
        return {}
    seg = frame_df.iloc[start_idx:end_idx + 1].copy()
    if seg.empty:
        return {}
    com_stats = _path_stats(seg, "com")
    l_stats = _path_stats(seg, "left_ankle")
    r_stats = _path_stats(seg, "right_ankle")
    return {
        "循环序号": cycle_id,
        "目标格": target_cell,
        "阶段": stage_name,
        "开始帧": int(seg["frame_id"].iloc[0]),
        "结束帧": int(seg["frame_id"].iloc[-1]),
        "帧数": int(len(seg)),
        "时长_s": _duration_s(seg, fps),
        "重心移动绝对距离_m": com_stats["abs_distance_m"],
        "重心左右移动距离_m": com_stats["left_right_distance_m"],
        "重心前后移动距离_m": com_stats["front_back_distance_m"],
        "左脚踝移动绝对距离_m": l_stats["abs_distance_m"],
        "左脚踝左右移动距离_m": l_stats["left_right_distance_m"],
        "左脚踝前后移动距离_m": l_stats["front_back_distance_m"],
        "右脚踝移动绝对距离_m": r_stats["abs_distance_m"],
        "右脚踝左右移动距离_m": r_stats["left_right_distance_m"],
        "右脚踝前后移动距离_m": r_stats["front_back_distance_m"],
        "重心移动速度均值_mps": _mean_or_nan(seg, "com_speed_mps"),
        "重心移动加速度均值_mps2": _mean_or_nan(seg, "com_acceleration_mps2"),
        "重心左右移动速度均值_mps": _mean_or_nan(seg, "com_vx_abs_mps"),
        "重心前后移动速度均值_mps": _mean_or_nan(seg, "com_vy_abs_mps"),
        "左脚踝移动速度均值_mps": _mean_or_nan(seg, "left_ankle_speed_mps"),
        "左脚踝移动加速度均值_mps2": _mean_or_nan(seg, "left_ankle_acceleration_mps2"),
        "左脚踝左右移动速度均值_mps": _mean_or_nan(seg, "left_ankle_vx_abs_mps"),
        "左脚踝前后移动速度均值_mps": _mean_or_nan(seg, "left_ankle_vy_abs_mps"),
        "右脚踝移动速度均值_mps": _mean_or_nan(seg, "right_ankle_speed_mps"),
        "右脚踝移动加速度均值_mps2": _mean_or_nan(seg, "right_ankle_acceleration_mps2"),
        "右脚踝左右移动速度均值_mps": _mean_or_nan(seg, "right_ankle_vx_abs_mps"),
        "右脚踝前后移动速度均值_mps": _mean_or_nan(seg, "right_ankle_vy_abs_mps"),
    }


def _asymmetry_index(left_val: float, right_val: float) -> float:
    if pd.isna(left_val) or pd.isna(right_val):
        return np.nan
    denom = (left_val + right_val) / 2.0
    if denom == 0:
        return 0.0
    return float(abs(left_val - right_val) / denom * 100.0)


# -----------------------------
# 逐帧参数
# -----------------------------
def build_frame_metrics(pose_df: pd.DataFrame, params: dict) -> pd.DataFrame:
    fps = float(params.get("fps", 60.0))
    dt = 1.0 / fps if fps > 0 else 0.0

    frame_ids = sorted(pose_df["frame_id"].unique())
    frame_df = pd.DataFrame({"frame_id": frame_ids})
    frame_df["time_s"] = frame_df["frame_id"] / fps

    # COM：优先 body_com，其次 pelvis，再次双髋中点
    for joint in [
        "body_com", "pelvis",
        "left_shoulder", "right_shoulder",
        "left_hip", "right_hip",
        "left_knee", "right_knee",
        "left_ankle", "right_ankle",
        "left_heel", "right_heel",
        "left_foot_index", "right_foot_index",
    ]:
        frame_df = _merge_joint_xyz(frame_df, pose_df, joint)

    frame_df["com_x"] = frame_df["body_com_x"]
    frame_df["com_y"] = frame_df["body_com_y"]
    frame_df["com_z"] = frame_df["body_com_z"]

    pelvis_mask = frame_df["com_x"].isna() & frame_df["pelvis_x"].notna()
    for axis in ["x", "y", "z"]:
        frame_df.loc[pelvis_mask, f"com_{axis}"] = frame_df.loc[pelvis_mask, f"pelvis_{axis}"]

    hip_mask = frame_df["com_x"].isna() & frame_df["left_hip_x"].notna() & frame_df["right_hip_x"].notna()
    for axis in ["x", "y", "z"]:
        frame_df.loc[hip_mask, f"com_{axis}"] = (frame_df.loc[hip_mask, f"left_hip_{axis}"] + frame_df.loc[hip_mask, f"right_hip_{axis}"]) / 2.0

    ground_z = params.get("ground_z")
    if ground_z is None:
        ground_z = _estimate_ground_z(pose_df)

    frame_df["left_foot_avg_z_m"] = frame_df[["left_heel_z", "left_foot_index_z"]].mean(axis=1)
    frame_df["right_foot_avg_z_m"] = frame_df[["right_heel_z", "right_foot_index_z"]].mean(axis=1)
    frame_df["left_clearance_m"] = (frame_df["left_foot_avg_z_m"] - float(ground_z)).clip(lower=0.0)
    frame_df["right_clearance_m"] = (frame_df["right_foot_avg_z_m"] - float(ground_z)).clip(lower=0.0)

    grid_cfg = params.get("grid", {})
    center_xy = grid_cfg.get("center_xy")
    if not center_xy:
        center_xy = _estimate_center_xy(
            frame_df,
            mode=str(grid_cfg.get("center_estimation_mode", "head_mean")),
        )
    center_xy = (float(center_xy[0]), float(center_xy[1]))
    cell_size = float(grid_cfg.get("cell_size_m", 0.9))
    total_size = float(grid_cfg.get("total_size_m", 2.7))
    if bool(grid_cfg.get("dynamic_total_size_m", False)):
        com_xy = frame_df[["com_x", "com_y"]].apply(pd.to_numeric, errors="coerce")
        if not com_xy.dropna().empty:
            x_span = float(com_xy["com_x"].quantile(0.95) - com_xy["com_x"].quantile(0.05))
            y_span = float(com_xy["com_y"].quantile(0.95) - com_xy["com_y"].quantile(0.05))
            inferred = max(cell_size * 3.0, max(x_span, y_span) * 1.25)
            total_size = max(total_size, inferred)

    for prefix in ["com", "left_ankle", "right_ankle"]:
        frame_df[f"{prefix}_cell"] = _locate_nine_grid_cell_series(
            frame_df[f"{prefix}_x"],
            frame_df[f"{prefix}_y"],
            center_xy=center_xy,
            cell_size=cell_size,
            total_size=total_size,
        )

    # 速度 / 加速度
    for prefix in ["com", "left_ankle", "right_ankle"]:
        frame_df[f"{prefix}_vx_mps"] = _derivative(frame_df[f"{prefix}_x"], dt)
        frame_df[f"{prefix}_vy_mps"] = _derivative(frame_df[f"{prefix}_y"], dt)
        frame_df[f"{prefix}_vz_mps"] = _derivative(frame_df[f"{prefix}_z"], dt)
        frame_df[f"{prefix}_vx_abs_mps"] = frame_df[f"{prefix}_vx_mps"].abs()
        frame_df[f"{prefix}_vy_abs_mps"] = frame_df[f"{prefix}_vy_mps"].abs()
        frame_df[f"{prefix}_horizontal_speed_mps"] = np.sqrt(frame_df[f"{prefix}_vx_mps"] ** 2 + frame_df[f"{prefix}_vy_mps"] ** 2)
        frame_df[f"{prefix}_speed_mps"] = np.sqrt(
            frame_df[f"{prefix}_vx_mps"] ** 2 + frame_df[f"{prefix}_vy_mps"] ** 2 + frame_df[f"{prefix}_vz_mps"] ** 2
        )
        frame_df[f"{prefix}_acceleration_mps2"] = _derivative(frame_df[f"{prefix}_speed_mps"], dt)

    # 关节角
    left_hip_angles = []
    right_hip_angles = []
    left_knee_angles = []
    right_knee_angles = []
    left_ankle_geom = []
    right_ankle_geom = []
    left_ankle_sag = []
    right_ankle_sag = []

    for _, row in frame_df.iterrows():
        ls = np.array([row.get("left_shoulder_x"), row.get("left_shoulder_y"), row.get("left_shoulder_z")], dtype=float)
        rs = np.array([row.get("right_shoulder_x"), row.get("right_shoulder_y"), row.get("right_shoulder_z")], dtype=float)
        lh = np.array([row.get("left_hip_x"), row.get("left_hip_y"), row.get("left_hip_z")], dtype=float)
        rh = np.array([row.get("right_hip_x"), row.get("right_hip_y"), row.get("right_hip_z")], dtype=float)
        lk = np.array([row.get("left_knee_x"), row.get("left_knee_y"), row.get("left_knee_z")], dtype=float)
        rk = np.array([row.get("right_knee_x"), row.get("right_knee_y"), row.get("right_knee_z")], dtype=float)
        la = np.array([row.get("left_ankle_x"), row.get("left_ankle_y"), row.get("left_ankle_z")], dtype=float)
        ra = np.array([row.get("right_ankle_x"), row.get("right_ankle_y"), row.get("right_ankle_z")], dtype=float)
        lheel = np.array([row.get("left_heel_x"), row.get("left_heel_y"), row.get("left_heel_z")], dtype=float)
        rheel = np.array([row.get("right_heel_x"), row.get("right_heel_y"), row.get("right_heel_z")], dtype=float)
        ltoe = np.array([row.get("left_foot_index_x"), row.get("left_foot_index_y"), row.get("left_foot_index_z")], dtype=float)
        rtoe = np.array([row.get("right_foot_index_x"), row.get("right_foot_index_y"), row.get("right_foot_index_z")], dtype=float)

        left_hip_angles.append(_vector_angle_deg(ls - lh, lk - lh))
        right_hip_angles.append(_vector_angle_deg(rs - rh, rk - rh))
        left_knee_angles.append(_vector_angle_deg(lh - lk, la - lk))
        right_knee_angles.append(_vector_angle_deg(rh - rk, ra - rk))
        left_ankle_geom.append(_vector_angle_deg(lk - la, ltoe - lheel))
        right_ankle_geom.append(_vector_angle_deg(rk - ra, rtoe - rheel))
        left_ankle_sag.append(_signed_sagittal_ankle_angle_deg(
            row.get("left_knee_y"), row.get("left_knee_z"),
            row.get("left_ankle_y"), row.get("left_ankle_z"),
            row.get("left_foot_index_y"), row.get("left_foot_index_z"),
        ))
        right_ankle_sag.append(_signed_sagittal_ankle_angle_deg(
            row.get("right_knee_y"), row.get("right_knee_z"),
            row.get("right_ankle_y"), row.get("right_ankle_z"),
            row.get("right_foot_index_y"), row.get("right_foot_index_z"),
        ))

    frame_df["left_hip_angle_deg"] = pd.to_numeric(pd.Series(left_hip_angles), errors="coerce")
    frame_df["right_hip_angle_deg"] = pd.to_numeric(pd.Series(right_hip_angles), errors="coerce")
    frame_df["left_knee_angle_deg"] = pd.to_numeric(pd.Series(left_knee_angles), errors="coerce")
    frame_df["right_knee_angle_deg"] = pd.to_numeric(pd.Series(right_knee_angles), errors="coerce")
    frame_df["left_ankle_angle_deg"] = pd.to_numeric(pd.Series(left_ankle_geom), errors="coerce")
    frame_df["right_ankle_angle_deg"] = pd.to_numeric(pd.Series(right_ankle_geom), errors="coerce")
    frame_df["left_ankle_sagittal_angle_deg"] = pd.to_numeric(pd.Series(left_ankle_sag), errors="coerce")
    frame_df["right_ankle_sagittal_angle_deg"] = pd.to_numeric(pd.Series(right_ankle_sag), errors="coerce")

    for angle_col in [
        "left_hip_angle_deg", "right_hip_angle_deg",
        "left_knee_angle_deg", "right_knee_angle_deg",
        "left_ankle_angle_deg", "right_ankle_angle_deg",
        "left_ankle_sagittal_angle_deg", "right_ankle_sagittal_angle_deg",
    ]:
        vel_col = angle_col.replace("_angle_deg", "_angular_velocity_deg_s")
        acc_col = angle_col.replace("_angle_deg", "_angular_acceleration_deg_s2")
        frame_df[vel_col] = _derivative(frame_df[angle_col], dt)
        frame_df[acc_col] = _derivative(frame_df[vel_col], dt)

    # 支撑状态（用于支撑期占比、步数）
    th = params.get("thresholds", {})
    contact_th = float(th.get("support_contact_threshold_m", 0.020))
    airborne_th = float(th.get("support_airborne_threshold_m", 0.040))
    support_min_frames = int(th.get("support_min_frames", 2))

    def _apply_hysteresis(clearance_series: pd.Series):
        states = []
        current = "support"
        pending = current
        pending_count = 0
        for val in clearance_series.tolist():
            c = _safe_num(val)
            if np.isnan(c):
                candidate = current
            elif c <= contact_th:
                candidate = "support"
            elif c >= airborne_th:
                candidate = "airborne"
            else:
                candidate = current

            if candidate == current:
                pending = current
                pending_count = 0
            else:
                if candidate == pending:
                    pending_count += 1
                else:
                    pending = candidate
                    pending_count = 1
                if pending_count >= support_min_frames:
                    current = pending
                    pending_count = 0
            states.append(current)
        return pd.Series(states, index=clearance_series.index, dtype=object)

    frame_df["left_support_state"] = _apply_hysteresis(frame_df["left_clearance_m"])
    frame_df["right_support_state"] = _apply_hysteresis(frame_df["right_clearance_m"])

    l_air = frame_df["left_support_state"].eq("airborne")
    r_air = frame_df["right_support_state"].eq("airborne")
    frame_df["support_mode"] = np.select(
        [l_air & r_air, l_air & (~r_air), (~l_air) & r_air],
        ["double_airborne", "left_airborne", "right_airborne"],
        default="double_support",
    )

    # 步数：落地事件
    frame_df["left_landing_event"] = (
        frame_df["left_support_state"].shift(1).eq("airborne") & frame_df["left_support_state"].eq("support")
    ).fillna(False).astype(int)
    frame_df["right_landing_event"] = (
        frame_df["right_support_state"].shift(1).eq("airborne") & frame_df["right_support_state"].eq("support")
    ).fillna(False).astype(int)
    frame_df["step_event_count"] = frame_df["left_landing_event"] + frame_df["right_landing_event"]

    # 关节力矩与功率（简化逆动力学）
    body = params.get("body", {})
    height_m = float(body.get("height_m", 1.75))
    weight_kg = float(body.get("weight_kg", 68.0))
    thigh_mass = weight_kg * 0.21
    shank_mass = weight_kg * 0.16
    thigh_length = height_m * 0.23
    shank_length = height_m * 0.21
    thigh_com_dist = thigh_length * 0.45
    shank_com_dist = shank_length * 0.43
    thigh_I = thigh_mass * (thigh_com_dist ** 2)
    shank_I = shank_mass * (shank_com_dist ** 2)

    # 段质心位置
    for side in ["left", "right"]:
        frame_df[f"{side}_thigh_com_x"] = frame_df[f"{side}_hip_x"] + 0.45 * (frame_df[f"{side}_knee_x"] - frame_df[f"{side}_hip_x"])
        frame_df[f"{side}_thigh_com_y"] = frame_df[f"{side}_hip_y"] + 0.45 * (frame_df[f"{side}_knee_y"] - frame_df[f"{side}_hip_y"])
        frame_df[f"{side}_thigh_com_z"] = frame_df[f"{side}_hip_z"] + 0.45 * (frame_df[f"{side}_knee_z"] - frame_df[f"{side}_hip_z"])

        frame_df[f"{side}_shank_com_x"] = frame_df[f"{side}_knee_x"] + 0.43 * (frame_df[f"{side}_ankle_x"] - frame_df[f"{side}_knee_x"])
        frame_df[f"{side}_shank_com_y"] = frame_df[f"{side}_knee_y"] + 0.43 * (frame_df[f"{side}_ankle_y"] - frame_df[f"{side}_knee_y"])
        frame_df[f"{side}_shank_com_z"] = frame_df[f"{side}_knee_z"] + 0.43 * (frame_df[f"{side}_ankle_z"] - frame_df[f"{side}_knee_z"])

        for seg in ["thigh_com", "shank_com"]:
            for axis in ["x", "y", "z"]:
                frame_df[f"{side}_{seg}_v{axis}_mps"] = _derivative(frame_df[f"{side}_{seg}_{axis}"], dt)
                frame_df[f"{side}_{seg}_a{axis}_mps2"] = _derivative(frame_df[f"{side}_{seg}_v{axis}_mps"], dt)

        frame_df[f"{side}_thigh_com_acc_mag_mps2"] = np.sqrt(
            frame_df[f"{side}_thigh_com_ax_mps2"] ** 2 +
            frame_df[f"{side}_thigh_com_ay_mps2"] ** 2 +
            frame_df[f"{side}_thigh_com_az_mps2"] ** 2
        )
        frame_df[f"{side}_shank_com_acc_mag_mps2"] = np.sqrt(
            frame_df[f"{side}_shank_com_ax_mps2"] ** 2 +
            frame_df[f"{side}_shank_com_ay_mps2"] ** 2 +
            frame_df[f"{side}_shank_com_az_mps2"] ** 2
        )

        hip_ang_acc_rad = np.deg2rad(frame_df[f"{side}_hip_angular_acceleration_deg_s2"])
        knee_ang_acc_rad = np.deg2rad(frame_df[f"{side}_knee_angular_acceleration_deg_s2"])
        hip_ang_vel_rad = np.deg2rad(frame_df[f"{side}_hip_angular_velocity_deg_s"])
        knee_ang_vel_rad = np.deg2rad(frame_df[f"{side}_knee_angular_velocity_deg_s"])

        frame_df[f"{side}_hip_torque_nm"] = thigh_mass * frame_df[f"{side}_thigh_com_acc_mag_mps2"] * thigh_com_dist + thigh_I * hip_ang_acc_rad
        frame_df[f"{side}_knee_torque_nm"] = shank_mass * frame_df[f"{side}_shank_com_acc_mag_mps2"] * shank_com_dist + shank_I * knee_ang_acc_rad

        frame_df[f"{side}_hip_torque_norm"] = frame_df[f"{side}_hip_torque_nm"] / (height_m * weight_kg)
        frame_df[f"{side}_knee_torque_norm"] = frame_df[f"{side}_knee_torque_nm"] / (height_m * weight_kg)

        frame_df[f"{side}_hip_power_w"] = frame_df[f"{side}_hip_torque_nm"] * hip_ang_vel_rad
        frame_df[f"{side}_knee_power_w"] = frame_df[f"{side}_knee_torque_nm"] * knee_ang_vel_rad

    frame_df["analysis_active"] = False
    frame_df["cycle_id"] = pd.NA
    frame_df["target_cell"] = pd.NA
    frame_df["movement_state"] = "未分析"
    frame_df["critical_event"] = ""

    return frame_df


# -----------------------------
# 规则切分
# -----------------------------

def segment_cycles_by_rules(frame_df: pd.DataFrame, params: dict):
    th = params.get("thresholds", {})
    entry_com_frames = int(th.get("entry_com_frames", 5))
    entry_ankle_frames = int(th.get("entry_ankle_frames", 8))
    static_com = float(th.get("static_com_speed_mps", 0.22))
    static_ankle = float(th.get("static_ankle_speed_mps", 0.30))
    static_frames = int(th.get("static_frames", 10))
    launch_com = float(th.get("launch_com_speed_mps", 0.35))
    launch_ankle = float(th.get("launch_ankle_speed_mps", 0.45))
    launch_disp = float(th.get("launch_displacement_m", 0.05))
    launch_frames = int(th.get("launch_frames", 5))

    df = frame_df.copy().reset_index(drop=True)

    for col in ["com_cell", "left_ankle_cell", "right_ankle_cell"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    com_run = _consecutive_lengths(df["com_cell"].tolist())
    la_run = _consecutive_lengths(df["left_ankle_cell"].tolist())
    ra_run = _consecutive_lengths(df["right_ankle_cell"].tolist())

    com_speed_col = "com_horizontal_speed_smooth_mps" if "com_horizontal_speed_smooth_mps" in df.columns else "com_horizontal_speed_mps"
    la_speed_col = "left_ankle_horizontal_speed_smooth_mps" if "left_ankle_horizontal_speed_smooth_mps" in df.columns else "left_ankle_horizontal_speed_mps"
    ra_speed_col = "right_ankle_horizontal_speed_smooth_mps" if "right_ankle_horizontal_speed_smooth_mps" in df.columns else "right_ankle_horizontal_speed_mps"

    # 停止：COM + 左踝 + 右踝 必须同时满足
    static_bool = (
        (df[com_speed_col] <= static_com) &
        (df[la_speed_col] <= static_ankle) &
        (df[ra_speed_col] <= static_ankle)
    ).fillna(False)

    def find_home_stop_window(start_idx: int) -> Optional[Tuple[int, int, Tuple[float, float]]]:
        # 第5格静止：COM在5格，或者双踝同时在5格，再叠加静止条件
        home_mask = (
            df["com_cell"].eq(5) |
            (df["left_ankle_cell"].eq(5) & df["right_ankle_cell"].eq(5))
        ).fillna(False)
        cond = home_mask & static_bool
        run_start = _first_run_start(cond, start_idx, static_frames)
        if run_start is None:
            return None
        run_end = run_start + static_frames - 1
        sub = df.iloc[run_start:run_end + 1]
        ref_xy = (float(sub["com_x"].mean()), float(sub["com_y"].mean()))
        return run_start, run_end, ref_xy

    def find_launch_from_ref(start_idx: int, ref_xy: Tuple[float, float]) -> Optional[int]:
        dist_from_ref = np.sqrt((df["com_x"] - ref_xy[0]) ** 2 + (df["com_y"] - ref_xy[1]) ** 2)

        # 启动：速度任一满足即可；但若位移阈值>0，则还需同时满足“离开停稳参考点”
        speed_cond = (
            (df[com_speed_col] >= launch_com) |
            (df[la_speed_col] >= launch_ankle) |
            (df[ra_speed_col] >= launch_ankle)
        ).fillna(False)

        if launch_disp is not None and launch_disp > 0:
            cond = speed_cond & (dist_from_ref >= launch_disp)
        else:
            cond = speed_cond

        return _first_run_start(cond.fillna(False), start_idx, launch_frames)

    def find_entry_event(start_idx: int, target_home: bool = False):
        for i in range(start_idx, len(df)):
            for source, cell_val, run_len, minlen in [
                ("com", df.at[i, "com_cell"], com_run[i], entry_com_frames),
                ("left_ankle", df.at[i, "left_ankle_cell"], la_run[i], entry_ankle_frames),
                ("right_ankle", df.at[i, "right_ankle_cell"], ra_run[i], entry_ankle_frames),
            ]:
                if pd.isna(cell_val):
                    continue
                cell = int(cell_val)
                cond_ok = (cell == 5) if target_home else (cell != 5)
                if cond_ok and run_len >= minlen:
                    return i, cell, source
        return None

    def find_target_stop(point1_idx: int, target_cell: int) -> Optional[int]:
        in_target = (
            df["com_cell"].eq(target_cell) |
            df["left_ankle_cell"].eq(target_cell) |
            df["right_ankle_cell"].eq(target_cell)
        ).fillna(False)
        cond = in_target & static_bool
        return _first_run_start(cond, point1_idx, static_frames)

    def find_home_return_event(start_idx: int):
        cond = (
            df["com_cell"].eq(5) |
            (df["left_ankle_cell"].eq(5) & df["right_ankle_cell"].eq(5))
        ).fillna(False)
        hit_idx = _first_run_start(cond, start_idx, entry_com_frames)
        if hit_idx is None:
            return None
        return hit_idx, 5, "home_return_event"

    def find_home_stop_after_return(start_idx: int) -> Optional[Tuple[int, int, Tuple[float, float], str]]:
        # 先找“回到第5格”，再找“第5格停止”；找不到停止时，用回到第5格兜底
        return_hit = find_home_return_event(start_idx)
        if return_hit is None:
            return None

        return_idx, _, _ = return_hit
        hit = find_home_stop_window(return_idx)
        if hit is None:
            ref_xy = (float(df.at[return_idx, "com_x"]), float(df.at[return_idx, "com_y"]))
            return return_idx, return_idx, ref_xy, "home_return_fallback"

        run_start, run_end, ref_xy = hit
        return run_start, run_end, ref_xy, "home_stop_window"

    def _annotate_cycles(cycles: List[dict]) -> pd.DataFrame:
        out = df.copy()
        for c in cycles:
            current_launch = c["state1_start_idx"]
            point2_idx = c["point2_idx"]
            point3_idx = c["point3_idx"]
            point4_idx = c["point4_idx"]
            target_cell = c["target_cell"]
            cycle_id = c["cycle_id"]

            out.loc[current_launch:point4_idx, "analysis_active"] = True
            out.loc[current_launch:point4_idx, "cycle_id"] = cycle_id
            out.loc[current_launch:point4_idx, "target_cell"] = int(target_cell)
            if point2_idx > current_launch:
                out.loc[current_launch:point2_idx - 1, "movement_state"] = "状态1_移动"
            if point3_idx > point2_idx:
                out.loc[point2_idx:point3_idx - 1, "movement_state"] = "状态2_停止"
            if point4_idx >= point3_idx:
                out.loc[point3_idx:point4_idx, "movement_state"] = "状态3_还原"

            out.at[c["point1_idx"], "critical_event"] = (str(out.at[c["point1_idx"], "critical_event"]) + "|临界点1_进入目标格").strip("|")
            out.at[point2_idx, "critical_event"] = (str(out.at[point2_idx, "critical_event"]) + "|临界点2_目标格停止").strip("|")
            out.at[point3_idx, "critical_event"] = (str(out.at[point3_idx, "critical_event"]) + "|临界点3_目标格启动").strip("|")
            out.at[point4_idx, "critical_event"] = (str(out.at[point4_idx, "critical_event"]) + "|临界点4_第5格停止").strip("|")
        return out

    cycles = []
    segmentation_source = "none"
    fallback_level = "none"
    non_home_cell_frames_pre = int(df["com_cell"].ne(5).fillna(False).sum())
    moving_signal_required = float(th.get("inhome_signal_ratio_min", 0.008))

    # -------- 严格规则优先 --------
    init_stop = find_home_stop_window(0)
    if init_stop is not None:
        _, init_stop_end, init_ref_xy = init_stop
        current_launch = find_launch_from_ref(init_stop_end + 1, init_ref_xy)
        cycle_id = 1

        while current_launch is not None and current_launch < len(df):
            point1 = find_entry_event(current_launch, target_home=False)
            if point1 is None:
                break
            point1_idx, target_cell, point1_src = point1

            point2_idx = find_target_stop(point1_idx, target_cell)
            if point2_idx is None:
                break

            stop_ref_sub = df.iloc[point2_idx:min(point2_idx + static_frames, len(df))]
            stop_ref_xy = (float(stop_ref_sub["com_x"].mean()), float(stop_ref_sub["com_y"].mean()))
            point3_idx = find_launch_from_ref(point2_idx + static_frames, stop_ref_xy)
            if point3_idx is None or point3_idx <= point2_idx:
                break

            point4 = find_home_stop_after_return(point3_idx)
            if point4 is None:
                break
            point4_idx, point4_stop_end, point4_ref_xy, point4_src = point4

            if point4_idx <= point3_idx:
                break

            cycles.append({
                "cycle_id": cycle_id,
                "target_cell": int(target_cell),
                "point1_source": point1_src,
                "point4_source": point4_src,
                "state1_start_idx": int(current_launch),
                "point1_idx": int(point1_idx),
                "point2_idx": int(point2_idx),
                "point3_idx": int(point3_idx),
                "point4_idx": int(point4_idx),
            })
            segmentation_source = "strict_rules"

            current_launch = find_launch_from_ref(point4_stop_end + 1, point4_ref_xy)
            cycle_id += 1

    # -------- 若严格规则失败，则使用“稳定格段”兜底 --------
    if not cycles:
        segments = []
        cells = df["com_cell"].tolist()
        start_idx = 0
        current_cell = cells[0] if len(cells) > 0 else np.nan
        for i in range(1, len(cells)):
            curr_missing = bool(pd.isna(cells[i]))
            prev_missing = bool(pd.isna(current_cell))
            same = False
            if curr_missing and prev_missing:
                same = True
            elif (not curr_missing) and (not prev_missing):
                same = bool(cells[i] == current_cell)
            if not same:
                if not pd.isna(current_cell):
                    segments.append((int(current_cell), start_idx, i - 1))
                start_idx = i
                current_cell = cells[i]
        if len(cells) > 0 and not pd.isna(current_cell):
            segments.append((int(current_cell), start_idx, len(cells) - 1))

        stable_segments = [(cell, s, e) for cell, s, e in segments if (e - s + 1) >= 3]

        cycle_id = 1
        for i in range(len(stable_segments) - 2):
            home_seg = stable_segments[i]
            target_seg = stable_segments[i + 1]
            back_seg = stable_segments[i + 2]
            if home_seg[0] != 5 or target_seg[0] == 5 or back_seg[0] != 5:
                continue

            _, hs, he = home_seg
            target_cell, ts, te = target_seg
            _, bs, be = back_seg

            state1_start_idx = max(hs, he - max(1, launch_frames) + 1)
            point1_idx = min(ts + max(1, entry_com_frames) - 1, te)

            target_slice = df.iloc[point1_idx:te + 1].copy()
            if target_slice.empty:
                continue
            stop_local_idx = int(target_slice[com_speed_col].astype(float).idxmin())
            point2_idx = stop_local_idx

            stop_ref_sub = df.iloc[point2_idx:min(point2_idx + static_frames, len(df))]
            stop_ref_xy = (float(stop_ref_sub["com_x"].mean()), float(stop_ref_sub["com_y"].mean()))
            point3_idx = find_launch_from_ref(point2_idx + 1, stop_ref_xy)
            if point3_idx is None:
                point3_idx = min(point2_idx + static_frames, te)

            back_slice = df.iloc[max(point3_idx, bs):be + 1].copy()
            if back_slice.empty:
                continue
            back_home_mask = (
                back_slice["com_cell"].eq(5) |
                (back_slice["left_ankle_cell"].eq(5) & back_slice["right_ankle_cell"].eq(5))
            ).fillna(False)
            back_static = (
                (back_slice[com_speed_col] <= static_com) &
                (back_slice[la_speed_col] <= static_ankle) &
                (back_slice[ra_speed_col] <= static_ankle) &
                back_home_mask
            ).fillna(False)
            back_runs = _extract_runs(back_static.reset_index(drop=True), static_frames)
            if back_runs:
                brs, _ = back_runs[0]
                point4_idx = max(point3_idx + 1, max(point3_idx, bs) + brs)
                point4_source = "fallback_home_stop"
            else:
                back_return = _first_run_start(back_home_mask.reset_index(drop=True), 0, entry_com_frames)
                if back_return is None:
                    continue
                point4_idx = max(point3_idx + 1, max(point3_idx, bs) + back_return)
                point4_source = "fallback_home_return"

            if point4_idx <= point3_idx:
                continue

            cycles.append({
                "cycle_id": cycle_id,
                "target_cell": int(target_cell),
                "point1_source": "fallback_com_segment",
                "point4_source": point4_source,
                "state1_start_idx": int(state1_start_idx),
                "point1_idx": int(point1_idx),
                "point2_idx": int(point2_idx),
                "point3_idx": int(point3_idx),
                "point4_idx": int(point4_idx),
            })
            segmentation_source = "stable_segments"
            cycle_id += 1

    # -------- 若仍失败，尝试“同格动作”兜底 --------
    if not cycles:
        step_events = pd.to_numeric(df.get("step_event_count", 0), errors="coerce").fillna(0) > 0
        moving_bool = (
            (df[com_speed_col] >= max(0.05, launch_com * 0.45)) |
            (df[la_speed_col] >= max(0.08, launch_ankle * 0.45)) |
            (df[ra_speed_col] >= max(0.08, launch_ankle * 0.45))
        ).fillna(False)
        moving_signal_ratio_local = float(moving_bool.mean()) if len(moving_bool) else 0.0
        moving_runs = _extract_runs(moving_bool, max(2, launch_frames))
        run_coverage_ratio = 0.0
        if len(df) > 0 and moving_runs:
            run_coverage_ratio = float(
                sum(max(0, e - s + 1) for s, e in moving_runs) / float(len(df))
            )
        step_event_ratio = float(step_events.mean()) if len(step_events) else 0.0
        moving_signal_required = max(
            float(th.get("inhome_signal_ratio_min", 0.008)),
            min(0.03, step_event_ratio * float(th.get("inhome_signal_step_ratio_scale", 0.6))),
            min(0.03, run_coverage_ratio * float(th.get("inhome_signal_run_ratio_scale", 0.5))),
        )
        anchors = sorted(
            set([int(i) for i in np.where(step_events.to_numpy())[0].tolist()] + [int(s) for s, _ in moving_runs])
        )
        min_gap = max(10, launch_frames * 3)
        filtered = []
        for idx in anchors:
            if not filtered or idx - filtered[-1] >= min_gap:
                filtered.append(idx)
        allow_weak_inhome = non_home_cell_frames_pre == 0 and bool(step_events.any())
        if len(filtered) >= 2 and (
            moving_signal_ratio_local >= moving_signal_required or allow_weak_inhome
        ):
            cycle_id = 1
            fallback_level = (
                "weak"
                if moving_signal_ratio_local < moving_signal_required
                else "standard"
            )
            for i in range(len(filtered) - 1):
                state1_start_idx = int(filtered[i])
                point4_idx = int(filtered[i + 1])
                if point4_idx - state1_start_idx < max(6, launch_frames * 2):
                    continue
                point2_idx = min(
                    point4_idx - 2,
                    state1_start_idx + max(1, static_frames // 2),
                )
                point3_idx = min(point4_idx - 1, point2_idx + 1)
                if point2_idx <= state1_start_idx or point4_idx <= point3_idx:
                    continue
                cycles.append({
                    "cycle_id": cycle_id,
                    "target_cell": 5,
                    "point1_source": "fallback_inhome_signal",
                    "point4_source": "fallback_inhome_signal",
                    "state1_start_idx": state1_start_idx,
                    "point1_idx": state1_start_idx,
                    "point2_idx": int(point2_idx),
                    "point3_idx": int(point3_idx),
                    "point4_idx": point4_idx,
                })
                cycle_id += 1
            if cycles:
                segmentation_source = (
                    "inhome_signal_fallback_weak"
                    if fallback_level == "weak"
                    else "inhome_signal_fallback"
                )

    out = _annotate_cycles(cycles)
    non_home_cell_frames = non_home_cell_frames_pre
    analysis_active_ratio = float(pd.to_numeric(out["analysis_active"], errors="coerce").fillna(0).mean()) if len(out) else 0.0
    moving_signal_ratio = float(moving_bool.mean()) if "moving_bool" in locals() else float(
        (
            (df[com_speed_col] >= max(0.05, launch_com * 0.45)) |
            (df[la_speed_col] >= max(0.08, launch_ankle * 0.45)) |
            (df[ra_speed_col] >= max(0.08, launch_ankle * 0.45))
        ).fillna(False).mean()
    )
    cycle_count = int(len(cycles))
    segmentation_status = "ok" if cycle_count > 0 else "failed"
    segmentation_reason = ""
    if segmentation_status == "failed":
        if non_home_cell_frames == 0:
            segmentation_reason = "all_frames_home_cell"
        elif moving_signal_ratio < moving_signal_required:
            segmentation_reason = "insufficient_motion_signal"
        else:
            segmentation_reason = "rules_not_matched"
    if segmentation_status == "failed":
        segmentation_confidence = "none"
    elif segmentation_source == "strict_rules":
        segmentation_confidence = "high"
    elif fallback_level == "weak":
        segmentation_confidence = "low"
    else:
        segmentation_confidence = "medium"

    diagnostics = {
        "segmentation_status": segmentation_status,
        "segmentation_reason": segmentation_reason,
        "segmentation_source": segmentation_source,
        "segmentation_confidence": segmentation_confidence,
        "fallback_level": fallback_level,
        "cycle_count": cycle_count,
        "non_home_cell_frames": non_home_cell_frames,
        "analysis_active_ratio": analysis_active_ratio,
        "moving_signal_ratio": moving_signal_ratio,
        "moving_signal_required_ratio": moving_signal_required,
    }
    return out, cycles, diagnostics


# -----------------------------
# 状态事件表
# -----------------------------
def build_state_event_table(cycles: List[dict], fps: float) -> pd.DataFrame:
    rows = []
    for c in cycles:
        state1_frames = max(0, c["point2_idx"] - c["state1_start_idx"])
        state2_frames = max(0, c["point3_idx"] - c["point2_idx"])
        state3_frames = max(0, c["point4_idx"] - c["point3_idx"] + 1)
        rows.append({
            "循环序号": c["cycle_id"],
            "目标格": c["target_cell"],
            "临界点1_进入目标格_帧": c["point1_idx"],
            "临界点2_目标格停止_帧": c["point2_idx"],
            "临界点3_目标格启动_帧": c["point3_idx"],
            "临界点4_第5格停止_帧": c["point4_idx"],
            "状态1_开始帧": c["state1_start_idx"],
            "状态1_结束帧": c["point2_idx"] - 1,
            "状态1_帧数": state1_frames,
            "状态1_时长_s": state1_frames / fps,
            "状态2_开始帧": c["point2_idx"],
            "状态2_结束帧": c["point3_idx"] - 1,
            "状态2_帧数": state2_frames,
            "状态2_时长_s": state2_frames / fps,
            "状态3_开始帧": c["point3_idx"],
            "状态3_结束帧": c["point4_idx"],
            "状态3_帧数": state3_frames,
            "状态3_时长_s": state3_frames / fps,
            "临界点1判定来源": c.get("point1_source"),
            "临界点4判定来源": c.get("point4_source"),
        })
    return pd.DataFrame(rows)


def build_speed_summary_table(frame_df: pd.DataFrame, cycles: List[dict], fps: float) -> pd.DataFrame:
    rows = []
    for c in cycles:
        rows.append(_segment_summary(frame_df, c["state1_start_idx"], c["point2_idx"] - 1, fps, "状态1_移动", c["cycle_id"], c["target_cell"]))
        rows.append(_segment_summary(frame_df, c["point3_idx"], c["point4_idx"], fps, "状态3_还原", c["cycle_id"], c["target_cell"]))
    rows = [r for r in rows if r]
    return pd.DataFrame(rows)


# -----------------------------
# 腾空参数
# -----------------------------
def build_airborne_event_table(frame_df: pd.DataFrame, params: dict) -> pd.DataFrame:
    th = params.get("thresholds", {})
    single_h = float(th.get("single_airborne_height_m", 0.025))
    single_frames = int(th.get("single_airborne_min_frames", 5))
    double_h = float(th.get("double_airborne_height_m", 0.020))
    double_frames = int(th.get("double_airborne_min_frames", 5))
    fps = float(params.get("fps", 60.0))

    left_mask = frame_df["left_clearance_m"] >= single_h
    right_mask = frame_df["right_clearance_m"] >= single_h
    double_mask = (frame_df["left_clearance_m"] >= double_h) & (frame_df["right_clearance_m"] >= double_h)

    rows = []
    event_id = 1

    for label, mask, min_frames in [
        ("左脚悬空", left_mask, single_frames),
        ("右脚悬空", right_mask, single_frames),
        ("双脚悬空", double_mask, double_frames),
    ]:
        for s_idx, e_idx in _extract_runs(mask, min_frames):
            sub = frame_df.iloc[s_idx:e_idx + 1].copy()
            if label == "左脚悬空":
                heights = sub["left_clearance_m"]
            elif label == "右脚悬空":
                heights = sub["right_clearance_m"]
            else:
                heights = sub[["left_clearance_m", "right_clearance_m"]].mean(axis=1)

            mid_idx = int((s_idx + e_idx) / 2)
            rows.append({
                "事件序号": event_id,
                "事件类型": label,
                "开始帧": int(sub["frame_id"].iloc[0]),
                "结束帧": int(sub["frame_id"].iloc[-1]),
                "帧数": int(len(sub)),
                "悬空时间_s": float(len(sub) / fps),
                "平均悬空高度_m": float(pd.to_numeric(heights, errors="coerce").mean()),
                "最大悬空高度_m": float(pd.to_numeric(heights, errors="coerce").max()),
                "循环序号": frame_df.iloc[mid_idx]["cycle_id"] if "cycle_id" in frame_df.columns else pd.NA,
                "所属状态": frame_df.iloc[mid_idx]["movement_state"] if "movement_state" in frame_df.columns else pd.NA,
            })
            event_id += 1

    return pd.DataFrame(rows)


def build_airborne_summary_table(airborne_events_df: pd.DataFrame) -> pd.DataFrame:
    def _max_row(event_type: str, col: str):
        sub = airborne_events_df[airborne_events_df["事件类型"] == event_type]
        if sub.empty or col not in sub.columns:
            return np.nan
        return float(pd.to_numeric(sub[col], errors="coerce").max())

    row = {
        "最大双脚悬空时间_s": _max_row("双脚悬空", "悬空时间_s"),
        "最大双脚悬空平均高度_m": _max_row("双脚悬空", "平均悬空高度_m"),
        "最大双脚悬空高度_m": _max_row("双脚悬空", "最大悬空高度_m"),
        "最大左脚悬空时间_s": _max_row("左脚悬空", "悬空时间_s"),
        "最大左脚悬空平均高度_m": _max_row("左脚悬空", "平均悬空高度_m"),
        "最大左脚悬空高度_m": _max_row("左脚悬空", "最大悬空高度_m"),
        "最大右脚悬空时间_s": _max_row("右脚悬空", "悬空时间_s"),
        "最大右脚悬空平均高度_m": _max_row("右脚悬空", "平均悬空高度_m"),
        "最大右脚悬空高度_m": _max_row("右脚悬空", "最大悬空高度_m"),
    }
    return pd.DataFrame([row])


# -----------------------------
# 关节参数
# -----------------------------
def build_joint_summary_table(frame_df: pd.DataFrame, cycles: List[dict], fps: float) -> pd.DataFrame:
    rows = []
    joint_map = {
        "左髋": ("left_hip_angle_deg", "left_hip_angular_velocity_deg_s", "left_hip_angular_acceleration_deg_s2"),
        "右髋": ("right_hip_angle_deg", "right_hip_angular_velocity_deg_s", "right_hip_angular_acceleration_deg_s2"),
        "左膝": ("left_knee_angle_deg", "left_knee_angular_velocity_deg_s", "left_knee_angular_acceleration_deg_s2"),
        "右膝": ("right_knee_angle_deg", "right_knee_angular_velocity_deg_s", "right_knee_angular_acceleration_deg_s2"),
        "左踝矢状面": ("left_ankle_sagittal_angle_deg", "left_ankle_sagittal_angular_velocity_deg_s", "left_ankle_sagittal_angular_acceleration_deg_s2"),
        "右踝矢状面": ("right_ankle_sagittal_angle_deg", "right_ankle_sagittal_angular_velocity_deg_s", "right_ankle_sagittal_angular_acceleration_deg_s2"),
    }

    for c in cycles:
        for stage_name, s_idx, e_idx in [
            ("状态1_移动", c["state1_start_idx"], c["point2_idx"] - 1),
            ("状态3_还原", c["point3_idx"], c["point4_idx"]),
        ]:
            seg = frame_df.iloc[s_idx:e_idx + 1].copy()
            if seg.empty:
                continue
            row = {
                "循环序号": c["cycle_id"],
                "目标格": c["target_cell"],
                "阶段": stage_name,
                "开始帧": int(seg["frame_id"].iloc[0]),
                "结束帧": int(seg["frame_id"].iloc[-1]),
                "帧数": int(len(seg)),
                "时长_s": float(len(seg) / fps),
            }
            for joint_name, cols in joint_map.items():
                angle_col, vel_col, acc_col = cols
                max_angle = _max_or_nan(seg, angle_col)
                min_angle = _min_or_nan(seg, angle_col)
                row[f"{joint_name}最小角度_deg"] = min_angle
                row[f"{joint_name}最大角度_deg"] = max_angle
                row[f"{joint_name}角度变化范围_deg"] = max_angle - min_angle if pd.notna(max_angle) and pd.notna(min_angle) else np.nan
                row[f"{joint_name}平均绝对角速度_deg_s"] = _abs_mean_or_nan(seg, vel_col)
                row[f"{joint_name}峰值绝对角速度_deg_s"] = _abs_max_or_nan(seg, vel_col)
                row[f"{joint_name}平均绝对角加速度_deg_s2"] = _abs_mean_or_nan(seg, acc_col)
                row[f"{joint_name}峰值绝对角加速度_deg_s2"] = _abs_max_or_nan(seg, acc_col)
            rows.append(row)
    return pd.DataFrame(rows)


# -----------------------------
# 总体参数
# -----------------------------
def build_overall_summary_table(frame_df: pd.DataFrame, speed_summary_df: pd.DataFrame) -> pd.DataFrame:
    active = frame_df[frame_df["movement_state"].isin(["状态1_移动", "状态3_还原"])].copy()
    move = frame_df[frame_df["movement_state"] == "状态1_移动"].copy()
    restore = frame_df[frame_df["movement_state"] == "状态3_还原"].copy()

    total_duration = _duration_s(active, fps=1.0)  # 稍后直接用 time ratio 不合适，这里改为帧计数后在下方修正
    fps = np.nan
    if "time_s" in frame_df.columns and len(frame_df) >= 2:
        dt = pd.to_numeric(frame_df["time_s"], errors="coerce").diff().dropna()
        if not dt.empty and dt.mean() > 0:
            fps = float(1.0 / dt.mean())
    if pd.isna(fps):
        fps = 60.0

    move_dist = _mean_or_nan(pd.DataFrame(), "x")  # 占位，不使用
    total_path = _path_stats(active, "com")["abs_distance_m"]
    move_path = _path_stats(move, "com")["abs_distance_m"]
    restore_path = _path_stats(restore, "com")["abs_distance_m"]

    total_time = len(active) / fps
    move_time = len(move) / fps
    restore_time = len(restore) / fps
    total_steps = int(pd.to_numeric(active["step_event_count"], errors="coerce").fillna(0).sum())

    row = {
        "运动耗时_s": total_time,
        "移动耗时_s": move_time,
        "还原耗时_s": restore_time,
        "移动总距离_m": total_path,
        "移动的步数": total_steps,
        "运动总平均速度_mps": total_path / total_time if total_time > 0 else np.nan,
        "移动总平均速度_mps": move_path / move_time if move_time > 0 else np.nan,
        "还原总平均速度_mps": restore_path / restore_time if restore_time > 0 else np.nan,
    }
    return pd.DataFrame([row])


# -----------------------------
# 评价参数
# -----------------------------
def build_evaluation_outputs(frame_df: pd.DataFrame, speed_summary_df: pd.DataFrame, overall_summary_df: pd.DataFrame, params: dict):
    body = params.get("body", {})
    height_m = float(body.get("height_m", 1.75))
    weight_kg = float(body.get("weight_kg", 68.0))
    th = params.get("thresholds", {})
    ratio_low = float(th.get("support_ratio_normal_low_pct", 60.0))
    ratio_high = float(th.get("support_ratio_normal_high_pct", 95.0))

    active = frame_df[frame_df["movement_state"].isin(["状态1_移动", "状态3_还原"])].copy()

    # 支撑期占比
    if active.empty:
        support_ratio_pct = np.nan
    else:
        support_frames = int((active["support_mode"] != "double_airborne").fillna(False).sum())
        support_ratio_pct = support_frames / len(active) * 100.0

    if pd.isna(support_ratio_pct):
        support_eval = "无有效数据"
    elif support_ratio_pct < ratio_low:
        support_eval = "支撑期占比偏低，可能存在失衡风险"
    elif support_ratio_pct > ratio_high:
        support_eval = "支撑期占比偏高，可能存在节奏拖滞和易疲劳问题"
    else:
        support_eval = "支撑期占比处于设定正常范围"

    # 对称性：多指标平均
    left_knee_rom = _max_or_nan(active, "left_knee_angle_deg") - _min_or_nan(active, "left_knee_angle_deg")
    right_knee_rom = _max_or_nan(active, "right_knee_angle_deg") - _min_or_nan(active, "right_knee_angle_deg")
    left_ankle_rom = _max_or_nan(active, "left_ankle_sagittal_angle_deg") - _min_or_nan(active, "left_ankle_sagittal_angle_deg")
    right_ankle_rom = _max_or_nan(active, "right_ankle_sagittal_angle_deg") - _min_or_nan(active, "right_ankle_sagittal_angle_deg")
    left_hip_torque_peak = _abs_max_or_nan(active, "left_hip_torque_nm")
    right_hip_torque_peak = _abs_max_or_nan(active, "right_hip_torque_nm")
    left_knee_torque_peak = _abs_max_or_nan(active, "left_knee_torque_nm")
    right_knee_torque_peak = _abs_max_or_nan(active, "right_knee_torque_nm")
    left_airborne_frames = int((active["support_mode"] == "left_airborne").fillna(False).sum())
    right_airborne_frames = int((active["support_mode"] == "right_airborne").fillna(False).sum())
    fps = float(params.get("fps", 60.0))
    left_airborne_time = left_airborne_frames / fps
    right_airborne_time = right_airborne_frames / fps

    symmetry_rows = [
        ("膝关节活动范围", left_knee_rom, right_knee_rom),
        ("踝关节活动范围", left_ankle_rom, right_ankle_rom),
        ("髋关节峰值力矩", left_hip_torque_peak, right_hip_torque_peak),
        ("膝关节峰值力矩", left_knee_torque_peak, right_knee_torque_peak),
        ("单脚支撑摆动时间", left_airborne_time, right_airborne_time),
    ]
    symmetry_detail = []
    for metric_name, left_val, right_val in symmetry_rows:
        symmetry_detail.append({
            "指标": metric_name,
            "左侧值": left_val,
            "右侧值": right_val,
            "不对称指数_pct": _asymmetry_index(left_val, right_val),
        })
    symmetry_detail_df = pd.DataFrame(symmetry_detail)
    symmetry_score = float(pd.to_numeric(symmetry_detail_df["不对称指数_pct"], errors="coerce").dropna().mean()) if not symmetry_detail_df.empty else np.nan

    # 过程能耗与效率
    if active.empty:
        process_energy_j = np.nan
    else:
        dt = 1.0 / fps
        power_cols = ["left_hip_power_w", "right_hip_power_w", "left_knee_power_w", "right_knee_power_w"]
        power_abs_sum = active[power_cols].abs().sum(axis=1)
        process_energy_j = float(power_abs_sum.sum() * dt)

    total_distance = float(overall_summary_df["移动总距离_m"].iloc[0]) if not overall_summary_df.empty else np.nan
    efficiency_pct = (total_distance * weight_kg / process_energy_j * 100.0) if pd.notna(process_energy_j) and process_energy_j > 0 else np.nan

    # 力矩汇总
    torque_summary = pd.DataFrame([{
        "左髋关节平均绝对力矩_Nm": _abs_mean_or_nan(active, "left_hip_torque_nm"),
        "左髋关节峰值绝对力矩_Nm": _abs_max_or_nan(active, "left_hip_torque_nm"),
        "右髋关节平均绝对力矩_Nm": _abs_mean_or_nan(active, "right_hip_torque_nm"),
        "右髋关节峰值绝对力矩_Nm": _abs_max_or_nan(active, "right_hip_torque_nm"),
        "左膝关节平均绝对力矩_Nm": _abs_mean_or_nan(active, "left_knee_torque_nm"),
        "左膝关节峰值绝对力矩_Nm": _abs_max_or_nan(active, "left_knee_torque_nm"),
        "右膝关节平均绝对力矩_Nm": _abs_mean_or_nan(active, "right_knee_torque_nm"),
        "右膝关节峰值绝对力矩_Nm": _abs_max_or_nan(active, "right_knee_torque_nm"),
        "左髋关节标准化力矩": _abs_mean_or_nan(active, "left_hip_torque_norm"),
        "右髋关节标准化力矩": _abs_mean_or_nan(active, "right_hip_torque_norm"),
        "左膝关节标准化力矩": _abs_mean_or_nan(active, "left_knee_torque_norm"),
        "右膝关节标准化力矩": _abs_mean_or_nan(active, "right_knee_torque_norm"),
    }])

    evaluation_summary = pd.DataFrame([{
        "循环次数": int(pd.to_numeric(frame_df["cycle_id"], errors="coerce").dropna().nunique()),
        "关节力矩_说明": "已按身高体重的简化逆动力学模型计算，详见 user_params.py 与 custom_analysis.py",
        "支撑期占比_pct": support_ratio_pct,
        "支撑期占比评价": support_eval,
        "步伐对称性_平均不对称指数_pct": symmetry_score,
        "过程能耗_J": process_energy_j,
        "步伐发力效率_pct": efficiency_pct,
        "身高_m": height_m,
        "体重_kg": weight_kg,
    }])

    return evaluation_summary, torque_summary, symmetry_detail_df


# -----------------------------
# 导出
# -----------------------------
def _save_table(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv":
        df.to_csv(path, index=False, encoding="utf-8-sig")
    else:
        df.to_excel(path, index=False)


_COLUMN_LABELS = {
    "time_s": "时间（s）",
    "frame_id": "帧号",
    "com_speed_mps": "重心移动速度（m/s）",
    "left_ankle_speed_mps": "左脚踝移动速度（m/s）",
    "right_ankle_speed_mps": "右脚踝移动速度（m/s）",
    "com_acceleration_mps2": "重心移动加速度（m/s²）",
    "left_ankle_acceleration_mps2": "左脚踝移动加速度（m/s²）",
    "right_ankle_acceleration_mps2": "右脚踝移动加速度（m/s²）",
    "left_clearance_m": "左脚离地高度（m）",
    "right_clearance_m": "右脚离地高度（m）",
    "left_hip_angle_deg": "左髋关节角度（°）",
    "right_hip_angle_deg": "右髋关节角度（°）",
    "left_knee_angle_deg": "左膝关节角度（°）",
    "right_knee_angle_deg": "右膝关节角度（°）",
    "left_ankle_sagittal_angle_deg": "左踝关节角度（°）",
    "right_ankle_sagittal_angle_deg": "右踝关节角度（°）",
    "left_knee_angular_velocity_deg_s": "左膝关节角速度（°/s）",
    "right_knee_angular_velocity_deg_s": "右膝关节角速度（°/s）",
    "left_ankle_sagittal_angular_velocity_deg_s": "左踝关节角速度（°/s）",
    "right_ankle_sagittal_angular_velocity_deg_s": "右踝关节角速度（°/s）",
    "left_hip_torque_nm": "左髋关节力矩（N·m）",
    "right_hip_torque_nm": "右髋关节力矩（N·m）",
    "left_knee_torque_nm": "左膝关节力矩（N·m）",
    "right_knee_torque_nm": "右膝关节力矩（N·m）",
    "left_hip_power_w": "左髋关节功率（W）",
    "right_hip_power_w": "右髋关节功率（W）",
    "left_knee_power_w": "左膝关节功率（W）",
    "right_knee_power_w": "右膝关节功率（W）",
}


def _pretty_label(col: str) -> str:
    return _COLUMN_LABELS.get(col, col)



def _safe_filename(name: str) -> str:
    invalid = '\\/:*?"<>|'
    out = ''.join('_' if ch in invalid else ch for ch in str(name))
    out = out.replace(chr(10), '_').replace(chr(13), '_').strip()
    return out or '未命名图片'



def _build_plot_json_payload(df: pd.DataFrame, x_col: str, y_cols: List[str], title: str, x_label: str, y_label: str):
    use_cols = [x_col] + [c for c in y_cols if c in df.columns]
    sub = df[use_cols].copy().replace({np.nan: None})
    return {
        "title": title,
        "x_col": x_col,
        "x_label": x_label,
        "y_cols": y_cols,
        "y_labels": {c: _pretty_label(c) for c in y_cols},
        "y_label": y_label,
        "records": sub.to_dict(orient="records"),
    }



def _save_plot_json(df: pd.DataFrame, x_col: str, y_cols: List[str], title: str, out_json_path: Path,
                    x_label: str = "时间（s）", y_label: str = "数值"):
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _build_plot_json_payload(df, x_col, y_cols, title, x_label, y_label)
    out_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")



def _plot_single_series(df: pd.DataFrame, x_col: str, y_col: str, title: str, out_path: Path,
                        x_label: str = "时间（s）", y_label: str = "数值", json_path: Optional[Path] = None):
    if y_col not in df.columns:
        return
    sub = df[[x_col, y_col]].dropna()
    if sub.empty:
        return

    _set_chinese_font()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 5))
    plt.plot(sub[x_col], sub[y_col], label=_pretty_label(y_col))
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.grid(alpha=0.25)
    handles, labels = plt.gca().get_legend_handles_labels()
    if labels:
        plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()

    if json_path is not None:
        _save_plot_json(sub, x_col, [y_col], title, json_path, x_label=x_label, y_label=y_label)



def _plot_line(df: pd.DataFrame, x_col: str, y_cols: List[str], title: str, out_path: Path,
               x_label: str = "时间（s）", y_label: str = "数值", include_split: bool = True,
               include_sum: bool = True):
    valid_cols = [c for c in y_cols if c in df.columns and not df[[x_col, c]].dropna().empty]
    if not valid_cols:
        return

    sub = df[[x_col] + valid_cols].copy().dropna(subset=[x_col])
    if sub.empty:
        return

    _set_chinese_font()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_dir = out_path.parent.parent / "图片数据JSON"
    split_dir = out_path.parent.parent / "单参数图片"

    # 组合图
    plt.figure(figsize=(12, 5))
    for col in valid_cols:
        plt.plot(sub[x_col], sub[col], label=_pretty_label(col))
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.grid(alpha=0.25)
    handles, labels = plt.gca().get_legend_handles_labels()
    if labels:
        plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    _save_plot_json(sub, x_col, valid_cols, title, json_dir / f"{_safe_filename(out_path.stem)}.json",
                    x_label=x_label, y_label=y_label)

    # 单参数拆分图
    if include_split:
        for col in valid_cols:
            single_title = f"{title}-{_pretty_label(col)}"
            single_png = split_dir / f"{_safe_filename(out_path.stem)}_{_safe_filename(_pretty_label(col))}.png"
            single_json = json_dir / f"{_safe_filename(out_path.stem)}_{_safe_filename(_pretty_label(col))}.json"
            _plot_single_series(sub, x_col, col, single_title, single_png,
                                x_label=x_label, y_label=y_label, json_path=single_json)

    # 总和图
    if include_sum and len(valid_cols) >= 2:
        sum_col = "__sum_plot_value__"
        sum_df = sub[[x_col] + valid_cols].copy()
        sum_df[sum_col] = sum_df[valid_cols].sum(axis=1, skipna=True)
        sum_title = f"{title}-总和"
        sum_png = split_dir / f"{_safe_filename(out_path.stem)}_总和.png"
        sum_json = json_dir / f"{_safe_filename(out_path.stem)}_总和.json"
        _plot_single_series(sum_df, x_col, sum_col, sum_title, sum_png,
                            x_label=x_label, y_label=y_label, json_path=sum_json)

def export_all_outputs(
    output_dir: Path,
    frame_df: pd.DataFrame,
    state_event_df: pd.DataFrame,
    speed_summary_df: pd.DataFrame,
    airborne_events_df: pd.DataFrame,
    airborne_summary_df: pd.DataFrame,
    joint_summary_df: pd.DataFrame,
    overall_summary_df: pd.DataFrame,
    evaluation_summary_df: pd.DataFrame,
    torque_summary_df: pd.DataFrame,
    symmetry_detail_df: pd.DataFrame,
    params: dict,
):
    output_dir = Path(output_dir)
    speed_dir = output_dir / "速度参数"
    airborne_dir = output_dir / "腾空参数"
    joint_dir = output_dir / "关节参数"
    overall_dir = output_dir / "总体参数"
    eval_dir = output_dir / "评价参数"

    # 速度
    speed_frame_cols = [
        "frame_id", "time_s", "cycle_id", "target_cell", "movement_state", "critical_event",
        "com_cell", "left_ankle_cell", "right_ankle_cell",
        "com_speed_mps", "com_horizontal_speed_mps", "com_acceleration_mps2",
        "com_vx_abs_mps", "com_vy_abs_mps",
        "left_ankle_speed_mps", "left_ankle_horizontal_speed_mps", "left_ankle_acceleration_mps2",
        "left_ankle_vx_abs_mps", "left_ankle_vy_abs_mps",
        "right_ankle_speed_mps", "right_ankle_horizontal_speed_mps", "right_ankle_acceleration_mps2",
        "right_ankle_vx_abs_mps", "right_ankle_vy_abs_mps",
        "step_event_count",
    ]
    _save_table(frame_df[[c for c in speed_frame_cols if c in frame_df.columns]], speed_dir / "01_逐帧速度参数表.xlsx")
    _save_table(state_event_df, speed_dir / "02_状态事件表.xlsx")
    _save_table(speed_summary_df, speed_dir / "03_状态速度汇总表.xlsx")

    # 腾空
    airborne_frame_cols = [
        "frame_id", "time_s", "cycle_id", "target_cell", "movement_state",
        "left_clearance_m", "right_clearance_m", "support_mode",
    ]
    _save_table(frame_df[[c for c in airborne_frame_cols if c in frame_df.columns]], airborne_dir / "01_逐帧腾空参数表.xlsx")
    _save_table(airborne_events_df, airborne_dir / "02_腾空事件表.xlsx")
    _save_table(airborne_summary_df, airborne_dir / "03_腾空汇总表.xlsx")

    # 关节
    joint_frame_cols = [
        "frame_id", "time_s", "cycle_id", "target_cell", "movement_state",
        "left_hip_angle_deg", "right_hip_angle_deg",
        "left_knee_angle_deg", "right_knee_angle_deg",
        "left_ankle_sagittal_angle_deg", "right_ankle_sagittal_angle_deg",
        "left_hip_angular_velocity_deg_s", "right_hip_angular_velocity_deg_s",
        "left_knee_angular_velocity_deg_s", "right_knee_angular_velocity_deg_s",
        "left_ankle_sagittal_angular_velocity_deg_s", "right_ankle_sagittal_angular_velocity_deg_s",
        "left_hip_angular_acceleration_deg_s2", "right_hip_angular_acceleration_deg_s2",
        "left_knee_angular_acceleration_deg_s2", "right_knee_angular_acceleration_deg_s2",
        "left_ankle_sagittal_angular_acceleration_deg_s2", "right_ankle_sagittal_angular_acceleration_deg_s2",
    ]
    _save_table(frame_df[[c for c in joint_frame_cols if c in frame_df.columns]], joint_dir / "01_逐帧关节参数表.xlsx")
    _save_table(joint_summary_df, joint_dir / "02_状态关节汇总表.xlsx")

    # 总体
    _save_table(overall_summary_df, overall_dir / "01_总体参数表.xlsx")

    # 评价
    eval_frame_cols = [
        "frame_id", "time_s", "cycle_id", "target_cell", "movement_state",
        "left_hip_torque_nm", "right_hip_torque_nm", "left_knee_torque_nm", "right_knee_torque_nm",
        "left_hip_power_w", "right_hip_power_w", "left_knee_power_w", "right_knee_power_w",
        "support_mode",
    ]
    _save_table(frame_df[[c for c in eval_frame_cols if c in frame_df.columns]], eval_dir / "01_逐帧评价参数表.xlsx")
    _save_table(evaluation_summary_df, eval_dir / "02_评价参数表.xlsx")
    _save_table(torque_summary_df, eval_dir / "03_关节力矩汇总表.xlsx")
    _save_table(symmetry_detail_df, eval_dir / "04_步伐对称性明细表.xlsx")

    # 绘图
    if params.get("plots", {}).get("enabled", True):
        _plot_line(frame_df, "time_s",
                   ["com_speed_mps", "left_ankle_speed_mps", "right_ankle_speed_mps"],
                   "速度变化曲线", speed_dir / "图片" / "速度变化曲线.png",
                   x_label="时间（s）", y_label="速度（m/s）")
        _plot_line(frame_df, "time_s",
                   ["com_acceleration_mps2", "left_ankle_acceleration_mps2", "right_ankle_acceleration_mps2"],
                   "加速度变化曲线", speed_dir / "图片" / "加速度变化曲线.png",
                   x_label="时间（s）", y_label="加速度（m/s²）")

        _plot_line(frame_df, "time_s",
                   ["left_clearance_m", "right_clearance_m"],
                   "足部离地高度曲线", airborne_dir / "图片" / "足部离地高度曲线.png",
                   x_label="时间（s）", y_label="离地高度（m）")

        _plot_line(frame_df, "time_s",
                   ["left_hip_angle_deg", "right_hip_angle_deg", "left_knee_angle_deg", "right_knee_angle_deg"],
                   "髋膝关节角度曲线", joint_dir / "图片" / "髋膝关节角度曲线.png",
                   x_label="时间（s）", y_label="角度（°）")
        _plot_line(frame_df, "time_s",
                   ["left_ankle_sagittal_angle_deg", "right_ankle_sagittal_angle_deg"],
                   "踝关节矢状面角度曲线", joint_dir / "图片" / "踝关节矢状面角度曲线.png",
                   x_label="时间（s）", y_label="角度（°）")
        _plot_line(frame_df, "time_s",
                   ["left_knee_angular_velocity_deg_s", "right_knee_angular_velocity_deg_s",
                    "left_ankle_sagittal_angular_velocity_deg_s", "right_ankle_sagittal_angular_velocity_deg_s"],
                   "关节角速度曲线", joint_dir / "图片" / "关节角速度曲线.png",
                   x_label="时间（s）", y_label="角速度（°/s）")

        _plot_line(frame_df, "time_s",
                   ["left_hip_torque_nm", "right_hip_torque_nm", "left_knee_torque_nm", "right_knee_torque_nm"],
                   "关节力矩曲线", eval_dir / "图片" / "关节力矩曲线.png",
                   x_label="时间（s）", y_label="力矩（N·m）")
        _plot_line(frame_df, "time_s",
                   ["left_hip_power_w", "right_hip_power_w", "left_knee_power_w", "right_knee_power_w"],
                   "关节功率曲线", eval_dir / "图片" / "关节功率曲线.png",
                   x_label="时间（s）", y_label="功率（W）")

    manifest = {
        "速度参数": [
            "01_逐帧速度参数表.xlsx：逐帧速度、加速度、状态与步数事件",
            "02_状态事件表.xlsx：临界点1/2/3/4与状态1/2/3的时间区间",
            "03_状态速度汇总表.xlsx：按状态1/3输出重心与左右脚踝距离、速度、加速度",
        ],
        "腾空参数": [
            "01_逐帧腾空参数表.xlsx：逐帧离地高度与支撑模式",
            "02_腾空事件表.xlsx：左脚/右脚/双脚悬空事件",
            "03_腾空汇总表.xlsx：最大悬空时间与高度",
        ],
        "关节参数": [
            "01_逐帧关节参数表.xlsx：逐帧髋/膝/踝角度、角速度、角加速度",
            "02_状态关节汇总表.xlsx：按状态1/3统计关节最小/最大/范围/角速度/角加速度",
        ],
        "总体参数": [
            "01_总体参数表.xlsx：运动耗时、移动耗时、还原耗时、总距离、步数、平均速度",
        ],
        "评价参数": [
            "01_逐帧评价参数表.xlsx：逐帧力矩、功率、支撑模式",
            "02_评价参数表.xlsx：循环次数、支撑期占比、对称性、过程能耗、发力效率",
            "03_关节力矩汇总表.xlsx：髋膝关节力矩统计",
            "04_步伐对称性明细表.xlsx：左右指标不对称指数",
        ],
        "附加图形输出": [
            "每个参数目录下新增 图片/：组合曲线图",
            "每个参数目录下新增 单参数图片/：每个指标单独曲线图 + 多指标总和曲线图",
            "每个参数目录下新增 图片数据JSON/：与每张图片对应的绘图数据 JSON",
        ],
    }
    (output_dir / "00_输出说明.json").write_text(
        pd.Series(manifest).to_json(force_ascii=False, indent=2),
        encoding="utf-8"
    )
