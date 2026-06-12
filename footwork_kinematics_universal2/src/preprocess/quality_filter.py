# -*- coding: utf-8 -*-
"""
3D 关节点预处理：长表转宽表、质量检查、异常标记、小段插值、低通滤波。

设计原则：
1. 不改变后续参数计算模块的接口，最终仍返回 frame_id / joint_name / x / y / z 的长表。
2. 额外导出宽表和质量检查表，便于人工检查。
3. 异常点先标记，再修复；短异常段插值，长异常段保留 NaN，不强行伪造数据。
4. 先处理坐标，再由后续模块求速度、加速度、角速度。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.io.read_pose3d_csv import find_first_column, normalize_joint_name

try:
    from scipy.signal import butter, filtfilt
except Exception:  # pragma: no cover - 仅在没有 scipy 时启用备用方案
    butter = None
    filtfilt = None


DEFAULT_KEY_JOINTS = [
    "body_com",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]

FOOT_JOINTS = {
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
}


# -----------------------------------------------------------------------------
# 基础工具
# -----------------------------------------------------------------------------
def _robust_median_mad_threshold(values: pd.Series, n_mad: float = 5.0) -> float:
    """中位数 + n*MAD 阈值。MAD 乘 1.4826 后约等于稳健标准差。"""
    v = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(v) == 0:
        return np.inf
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    robust_sigma = 1.4826 * mad
    if robust_sigma <= 1e-12:
        return np.inf
    return med + n_mad * robust_sigma


def _run_lengths(mask: pd.Series) -> pd.Series:
    """计算布尔序列中 True 连续段长度；False 的位置返回 0。"""
    mask = mask.fillna(False).astype(bool)
    group_id = (mask != mask.shift()).cumsum()
    lengths = mask.groupby(group_id).transform("sum")
    return lengths.where(mask, 0).astype(int)


def _safe_numeric(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _flatten_pivot_columns(cols) -> List[str]:
    """把 pivot 后的多级列名整理成 joint_axis，例如 body_com_x。"""
    out = []
    for axis, joint in cols:
        out.append(f"{joint}_{axis}")
    return out


def _long_to_wide_xyz(long_df: pd.DataFrame, value_cols: Tuple[str, str, str] = ("x", "y", "z")) -> pd.DataFrame:
    """长表转宽表：每帧一行，每个关节点的 x/y/z 为独立列。"""
    wide = long_df.pivot_table(
        index="frame_id",
        columns="joint_name",
        values=list(value_cols),
        aggfunc="mean",
    )
    wide.columns = _flatten_pivot_columns(wide.columns)
    wide = wide.reset_index().sort_values("frame_id").reset_index(drop=True)
    return wide


def _lowpass_filter_series(series: pd.Series, fps: float, cutoff_hz: float, order: int) -> pd.Series:
    """
    对单列坐标做零相位 Butterworth 低通滤波。
    若 scipy 不可用或数据太短，则退化为居中滚动均值，避免程序中断。
    """
    s = pd.to_numeric(series, errors="coerce")
    out = pd.Series(np.nan, index=s.index, dtype=float)
    finite = s.dropna()
    if finite.empty:
        return out

    # 为了 filtfilt 连续运行，临时全量插值；后面会把长异常段重新置 NaN。
    filled = s.interpolate(method="linear", limit_direction="both")
    arr = filled.to_numpy(dtype=float)

    if fps <= 0 or cutoff_hz <= 0:
        return pd.Series(arr, index=s.index, dtype=float)

    nyq = 0.5 * fps
    normal_cutoff = min(float(cutoff_hz) / nyq, 0.99)
    order = max(int(order), 1)

    if butter is not None and filtfilt is not None and len(arr) > max(12, order * 6):
        try:
            b, a = butter(order, normal_cutoff, btype="low", analog=False)
            filtered = filtfilt(b, a, arr)
            return pd.Series(filtered, index=s.index, dtype=float)
        except Exception:
            pass

    # 备用方案：简单滚动均值，不如 Butterworth，但至少可运行。
    window = max(int(round(fps / max(cutoff_hz, 1.0))), 3)
    if window % 2 == 0:
        window += 1
    return filled.rolling(window=window, center=True, min_periods=1).mean()


def _make_bad_reason(row: pd.Series) -> str:
    reasons = []
    if bool(row.get("bad_valid", False)):
        reasons.append("valid=0")
    if bool(row.get("bad_reproj", False)):
        reasons.append("重投影误差偏大")
    if bool(row.get("bad_ray_gap", False)):
        reasons.append("左右相机射线间距偏大")
    if bool(row.get("bad_spike", False)):
        reasons.append("坐标突变/速度异常")
    if bool(row.get("bad_height", False)):
        reasons.append("足部高度异常")
    return "；".join(reasons)


# -----------------------------------------------------------------------------
# 主函数
# -----------------------------------------------------------------------------
def preprocess_pose3d_long(
    input_csv: str | Path,
    output_dir: str | Path,
    params: Optional[dict] = None,
    fps: float = 60.0,
) -> pd.DataFrame:
    """
    读取原始 3D 长表 CSV，并完成：
    1. 关节点名称标准化；
    2. 长表转宽表导出；
    3. 质量检查与异常标记；
    4. 短异常段插值修复；
    5. 坐标低通滤波；
    6. 返回滤波后的长表，供后续 build_frame_metrics 使用。
    """
    params = params or {}
    pp = params.get("preprocess", {}) or {}

    input_csv = Path(input_csv)
    output_dir = Path(output_dir)
    preprocess_dir = output_dir / "预处理结果"
    preprocess_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------
    # 1. 读取并标准化原始长表
    # -------------------------
    raw = pd.read_csv(input_csv, encoding="utf-8-sig")

    frame_col = find_first_column(raw, ["frame_id", "frame", "frame_idx", "index"])
    joint_col = find_first_column(raw, ["joint_name", "joint", "name", "landmark"])
    x_col = find_first_column(raw, ["x", "X"])
    y_col = find_first_column(raw, ["y", "Y"])
    z_col = find_first_column(raw, ["z", "Z"])

    missing = [k for k, v in {
        "frame_id": frame_col,
        "joint_name": joint_col,
        "x": x_col,
        "y": y_col,
        "z": z_col,
    }.items() if v is None]
    if missing:
        raise ValueError(f"输入 CSV 缺少必要列：{missing}")

    # 尽量保留重建质量列。
    optional_cols = {
        "reproj_err_left_px": find_first_column(raw, ["reproj_err_left_px", "left_reproj_err_px", "reproj_left_px"]),
        "reproj_err_right_px": find_first_column(raw, ["reproj_err_right_px", "right_reproj_err_px", "reproj_right_px"]),
        "ray_gap_m": find_first_column(raw, ["ray_gap_m", "ray_gap", "triangulation_gap_m"]),
        "valid": find_first_column(raw, ["valid", "is_valid"]),
    }

    keep_cols = [frame_col, joint_col, x_col, y_col, z_col] + [c for c in optional_cols.values() if c is not None]
    df = raw[keep_cols].copy()

    rename_map = {
        frame_col: "frame_id",
        joint_col: "joint_name_raw",
        x_col: "x_raw",
        y_col: "y_raw",
        z_col: "z_raw",
    }
    for std_name, old_col in optional_cols.items():
        if old_col is not None:
            rename_map[old_col] = std_name
    df = df.rename(columns=rename_map)

    df["joint_name"] = df["joint_name_raw"].apply(normalize_joint_name)
    numeric_cols = ["frame_id", "x_raw", "y_raw", "z_raw", "reproj_err_left_px", "reproj_err_right_px", "ray_gap_m", "valid"]
    df = _safe_numeric(df, numeric_cols)
    df = df.dropna(subset=["frame_id", "joint_name"]).copy()
    df["frame_id"] = df["frame_id"].astype(int)

    # 同一帧同一关节若有重复，取平均；质量列取最大值/最小 valid。
    agg = {"x_raw": "mean", "y_raw": "mean", "z_raw": "mean"}
    if "reproj_err_left_px" in df.columns:
        agg["reproj_err_left_px"] = "max"
    if "reproj_err_right_px" in df.columns:
        agg["reproj_err_right_px"] = "max"
    if "ray_gap_m" in df.columns:
        agg["ray_gap_m"] = "max"
    if "valid" in df.columns:
        agg["valid"] = "min"

    df = (
        df.groupby(["frame_id", "joint_name"], as_index=False)
        .agg(agg)
        .sort_values(["frame_id", "joint_name"])
        .reset_index(drop=True)
    )

    # 宽表：原始坐标。
    raw_for_wide = df.rename(columns={"x_raw": "x", "y_raw": "y", "z_raw": "z"})[
        ["frame_id", "joint_name", "x", "y", "z"]
    ]
    wide_raw = _long_to_wide_xyz(raw_for_wide)

    if bool(pp.get("export_intermediate", True)):
        wide_raw.to_csv(preprocess_dir / "01_宽表原始坐标.csv", index=False, encoding="utf-8-sig")

    # -------------------------
    # 2. 质量检查：重建误差、突变、高度
    # -------------------------
    key_joints = pp.get("key_joints") or DEFAULT_KEY_JOINTS
    key_joints = [normalize_joint_name(j) for j in key_joints]

    max_gap_frames = int(pp.get("max_interpolate_gap_frames", 5))
    cutoff_hz = float(pp.get("butterworth_cutoff_hz", 8.0))
    order = int(pp.get("butterworth_order", 4))
    spike_mad_n = float(pp.get("spike_mad_n", 5.0))

    max_speed_default = float(pp.get("max_joint_speed_mps", 10.0))
    max_speed_body_com = float(pp.get("max_body_com_speed_mps", 6.0))
    foot_z_min = float(pp.get("foot_z_min_m", -0.05))
    foot_z_max = float(pp.get("foot_z_max_m", 0.35))

    reproj_fixed_th = pp.get("reproj_err_px_threshold", None)
    ray_gap_fixed_th = pp.get("ray_gap_m_threshold", None)
    reproj_mad_n = float(pp.get("reproj_mad_n", 3.0))
    ray_gap_mad_n = float(pp.get("ray_gap_mad_n", 3.0))

    if reproj_fixed_th is not None:
        reproj_th = float(reproj_fixed_th)
    else:
        reproj_candidates = []
        for c in ["reproj_err_left_px", "reproj_err_right_px"]:
            if c in df.columns:
                reproj_candidates.append(pd.to_numeric(df[c], errors="coerce"))
        reproj_th = _robust_median_mad_threshold(pd.concat(reproj_candidates), reproj_mad_n) if reproj_candidates else np.inf

    if ray_gap_fixed_th is not None:
        ray_gap_th = float(ray_gap_fixed_th)
    else:
        ray_gap_th = _robust_median_mad_threshold(df.get("ray_gap_m", pd.Series(dtype=float)), ray_gap_mad_n) if "ray_gap_m" in df.columns else np.inf

    df["bad_valid"] = False
    if "valid" in df.columns:
        df["bad_valid"] = pd.to_numeric(df["valid"], errors="coerce").fillna(1).astype(float) <= 0

    df["bad_reproj"] = False
    if "reproj_err_left_px" in df.columns:
        df["bad_reproj"] |= pd.to_numeric(df["reproj_err_left_px"], errors="coerce") > reproj_th
    if "reproj_err_right_px" in df.columns:
        df["bad_reproj"] |= pd.to_numeric(df["reproj_err_right_px"], errors="coerce") > reproj_th

    df["bad_ray_gap"] = False
    if "ray_gap_m" in df.columns:
        df["bad_ray_gap"] = pd.to_numeric(df["ray_gap_m"], errors="coerce") > ray_gap_th

    df["bad_spike"] = False
    df["bad_height"] = False
    df["joint_speed_mps_for_qc"] = np.nan

    all_frames = np.arange(int(df["frame_id"].min()), int(df["frame_id"].max()) + 1)
    processed_parts = []
    quality_parts = []

    for joint_name, sub in df.groupby("joint_name", sort=True):
        sub = sub.sort_values("frame_id").set_index("frame_id").reindex(all_frames)
        sub.index.name = "frame_id"
        sub["joint_name"] = joint_name

        for c in ["x_raw", "y_raw", "z_raw"]:
            sub[c] = pd.to_numeric(sub[c], errors="coerce")

        # 中心差分速度，用于坐标突变检查。
        x_tmp = sub["x_raw"].interpolate(limit_direction="both")
        y_tmp = sub["y_raw"].interpolate(limit_direction="both")
        z_tmp = sub["z_raw"].interpolate(limit_direction="both")
        if len(sub) >= 3 and fps > 0:
            vx = np.gradient(x_tmp.to_numpy(dtype=float), 1.0 / fps)
            vy = np.gradient(y_tmp.to_numpy(dtype=float), 1.0 / fps)
            vz = np.gradient(z_tmp.to_numpy(dtype=float), 1.0 / fps)
            speed = pd.Series(np.sqrt(vx ** 2 + vy ** 2 + vz ** 2), index=sub.index)
        else:
            speed = pd.Series(np.nan, index=sub.index)
        sub["joint_speed_mps_for_qc"] = speed

        if joint_name in key_joints:
            hard_th = max_speed_body_com if joint_name == "body_com" else max_speed_default
            mad_th = _robust_median_mad_threshold(speed, spike_mad_n)
            spike_th = min(hard_th, mad_th) if np.isfinite(mad_th) else hard_th
            sub["bad_spike"] = speed > spike_th
        else:
            sub["bad_spike"] = False

        if joint_name in FOOT_JOINTS:
            sub["bad_height"] = (sub["z_raw"] < foot_z_min) | (sub["z_raw"] > foot_z_max)
        else:
            sub["bad_height"] = False

        # reindex 后质量列可能有 NaN，补成 False。
        for flag_col in ["bad_valid", "bad_reproj", "bad_ray_gap", "bad_spike", "bad_height"]:
            if flag_col not in sub.columns:
                sub[flag_col] = False
            sub[flag_col] = sub[flag_col].fillna(False).astype(bool)

        sub["is_bad"] = sub[["bad_valid", "bad_reproj", "bad_ray_gap", "bad_spike", "bad_height"]].any(axis=1)
        sub["bad_reason"] = sub.apply(_make_bad_reason, axis=1)

        # -------------------------
        # 3. 小段异常插值修复
        # -------------------------
        bad_run_len = _run_lengths(sub["is_bad"])
        short_bad = sub["is_bad"] & (bad_run_len <= max_gap_frames)
        long_bad = sub["is_bad"] & (bad_run_len > max_gap_frames)
        missing_original = sub[["x_raw", "y_raw", "z_raw"]].isna().any(axis=1)

        for axis in ["x", "y", "z"]:
            raw_col = f"{axis}_raw"
            interp_col = f"{axis}_interp"
            filt_col = f"{axis}_filtered"

            s = sub[raw_col].copy()
            # 短异常段先置空，再用 limit 控制只修复短缺口。
            s.loc[short_bad] = np.nan
            repaired = s.interpolate(method="linear", limit=max_gap_frames, limit_direction="both")
            # 长异常段不强行修复，保留 NaN。
            repaired.loc[long_bad | missing_original] = np.nan
            sub[interp_col] = repaired

            filtered = _lowpass_filter_series(repaired, fps=fps, cutoff_hz=cutoff_hz, order=order)
            # 长异常段仍然保留 NaN，避免后续误以为这些点可靠。
            filtered.loc[long_bad | missing_original] = np.nan
            sub[filt_col] = filtered

        # 输出给后续分析用的 x/y/z。
        sub["x"] = sub["x_filtered"]
        sub["y"] = sub["y_filtered"]
        sub["z"] = sub["z_filtered"]

        processed_parts.append(sub.reset_index())
        quality_cols = [
            "frame_id", "joint_name",
            "bad_valid", "bad_reproj", "bad_ray_gap", "bad_spike", "bad_height",
            "is_bad", "bad_reason", "joint_speed_mps_for_qc",
        ]
        existing_quality_cols = [c for c in quality_cols if c in sub.reset_index().columns]
        quality_parts.append(sub.reset_index()[existing_quality_cols])

    processed = pd.concat(processed_parts, ignore_index=True)
    quality_df = pd.concat(quality_parts, ignore_index=True)

    # 保留有效帧/关节行；长异常段 x/y/z 可能是 NaN，但行本身保留。
    processed = processed.dropna(subset=["frame_id", "joint_name"]).copy()
    processed["frame_id"] = processed["frame_id"].astype(int)
    processed["time_s"] = processed["frame_id"] / float(fps)

    # 宽表：插值滤波后坐标。
    wide_filtered = _long_to_wide_xyz(processed[["frame_id", "joint_name", "x", "y", "z"]])

    # 每帧异常汇总。
    frame_summary = (
        quality_df.groupby("frame_id", as_index=False)
        .agg(
            异常关节点数=("is_bad", "sum"),
            坐标突变关节点数=("bad_spike", "sum"),
            足部高度异常关节点数=("bad_height", "sum"),
            重投影异常关节点数=("bad_reproj", "sum"),
            射线间距异常关节点数=("bad_ray_gap", "sum"),
            valid异常关节点数=("bad_valid", "sum"),
        )
        .sort_values("frame_id")
    )

    # 只导出有问题的明细更方便检查；同时另存完整质量表。
    quality_bad_only = quality_df[quality_df["is_bad"]].copy()

    if bool(pp.get("export_intermediate", True)):
        quality_df.to_csv(preprocess_dir / "02_质量检查明细_全部.csv", index=False, encoding="utf-8-sig")
        quality_bad_only.to_csv(preprocess_dir / "03_质量检查明细_仅异常.csv", index=False, encoding="utf-8-sig")
        frame_summary.to_csv(preprocess_dir / "04_异常帧汇总.csv", index=False, encoding="utf-8-sig")
        wide_filtered.to_csv(preprocess_dir / "05_宽表插值滤波后坐标.csv", index=False, encoding="utf-8-sig")

        info = {
            "input_csv": str(input_csv),
            "fps": fps,
            "wide_raw_csv": "01_宽表原始坐标.csv",
            "quality_all_csv": "02_质量检查明细_全部.csv",
            "quality_bad_only_csv": "03_质量检查明细_仅异常.csv",
            "frame_summary_csv": "04_异常帧汇总.csv",
            "wide_filtered_csv": "05_宽表插值滤波后坐标.csv",
            "rules": {
                "max_interpolate_gap_frames": max_gap_frames,
                "butterworth_cutoff_hz": cutoff_hz,
                "butterworth_order": order,
                "spike_mad_n": spike_mad_n,
                "max_body_com_speed_mps": max_speed_body_com,
                "max_joint_speed_mps": max_speed_default,
                "foot_z_min_m": foot_z_min,
                "foot_z_max_m": foot_z_max,
                "reproj_err_px_threshold_used": None if not np.isfinite(reproj_th) else float(reproj_th),
                "ray_gap_m_threshold_used": None if not np.isfinite(ray_gap_th) else float(ray_gap_th),
            },
            "summary": {
                "n_frames": int(wide_filtered.shape[0]),
                "n_joints": int(processed["joint_name"].nunique()),
                "n_quality_rows": int(len(quality_df)),
                "n_bad_rows": int(quality_df["is_bad"].sum()),
                "n_bad_frames": int((frame_summary["异常关节点数"] > 0).sum()),
            },
        }
        with open(preprocess_dir / "06_预处理说明.json", "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

    # 后续分析仍用长表。
    out_cols = ["frame_id", "joint_name", "x", "y", "z", "time_s"]
    return processed[out_cols].sort_values(["frame_id", "joint_name"]).reset_index(drop=True)
