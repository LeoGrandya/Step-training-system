# -*- coding: utf-8 -*-
"""
数据 I/O 层：读取宽表 CSV，返回长表 DataFrame。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


# 标准关节名（与 CSV 列名中的 joint 部分对应）
ALL_JOINTS = [
    "body_com",
    "pelvis",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
    "left_shoulder", "right_shoulder",
]


def wide_to_long(csv_path: Path, fps: float = 60.0) -> pd.DataFrame:
    """
    读取宽表 CSV（每帧一行，列如 body_com_x, left_hip_y ...）
    → 转为长表（frame_id, joint_name, x, y, z, time_s）

    同时处理缺失关节（填 NaN）。
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # 确保 frame_id 列存在
    id_col = "frame_id"
    value_cols = [c for c in df.columns if c != id_col]

    # 宽→长：melt 所有坐标列
    long = df.melt(id_vars=[id_col], value_vars=value_cols,
                   var_name="coord", value_name="value")
    long = long.dropna(subset=["value"])

    # 从 "body_com_x" → joint_name="body_com", axis="x"
    # 最后一个 _ 分隔 axis
    long["joint_name"] = long["coord"].str.rsplit("_", n=1).str[0]
    long["axis"] = long["coord"].str.rsplit("_", n=1).str[1]

    # pivot 回 x/y/z 三列
    long = long.pivot_table(
        index=["frame_id", "joint_name"],
        columns="axis",
        values="value",
        aggfunc="mean",
    ).reset_index()

    # 确保有 x/y/z 列
    for col in ["x", "y", "z"]:
        if col not in long.columns:
            long[col] = np.nan

    long = long[["frame_id", "joint_name", "x", "y", "z"]].copy()
    long["frame_id"] = long["frame_id"].astype(int)
    long["time_s"] = long["frame_id"] / float(fps)

    return long.sort_values(["frame_id", "joint_name"]).reset_index(drop=True)


def build_wide_frame(pose_long: pd.DataFrame, fps: float) -> pd.DataFrame:
    """
    从长表构建逐帧宽表 DataFrame。

    输出列（每帧一行）：
    - frame_id, time_s
    - {joint}_x, {joint}_y, {joint}_z  (所有可用关节)
    - com_x, com_y, com_z  (智能选择：body_com > pelvis > 双髋中点)
    """
    frame_ids = sorted(pose_long["frame_id"].unique())
    frame_df = pd.DataFrame({"frame_id": frame_ids})
    frame_df["time_s"] = frame_df["frame_id"] / fps

    # 提取每个关节的 x/y/z
    for joint in ALL_JOINTS:
        sub = pose_long[pose_long["joint_name"] == joint][["frame_id", "x", "y", "z"]].copy()
        if sub.empty:
            frame_df[f"{joint}_x"] = np.nan
            frame_df[f"{joint}_y"] = np.nan
            frame_df[f"{joint}_z"] = np.nan
        else:
            sub = sub.rename(columns={"x": f"{joint}_x", "y": f"{joint}_y", "z": f"{joint}_z"})
            frame_df = frame_df.merge(sub, on="frame_id", how="left")

    # COM 三级回退
    frame_df["com_x"] = frame_df["body_com_x"]
    frame_df["com_y"] = frame_df["body_com_y"]
    frame_df["com_z"] = frame_df["body_com_z"]

    pelvis_mask = frame_df["com_x"].isna() & frame_df["pelvis_x"].notna()
    for axis in ["x", "y", "z"]:
        frame_df.loc[pelvis_mask, f"com_{axis}"] = frame_df.loc[pelvis_mask, f"pelvis_{axis}"]

    hip_mask = (
        frame_df["com_x"].isna()
        & frame_df["left_hip_x"].notna()
        & frame_df["right_hip_x"].notna()
    )
    for axis in ["x", "y", "z"]:
        frame_df.loc[hip_mask, f"com_{axis}"] = (
            frame_df.loc[hip_mask, f"left_hip_{axis}"]
            + frame_df.loc[hip_mask, f"right_hip_{axis}"]
        ) / 2.0

    return frame_df
