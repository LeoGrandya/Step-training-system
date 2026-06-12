# -*- coding: utf-8 -*-
"""数据后处理流水线：对宽表 DataFrame 执行 异常值→插值→滤波，返回处理后的 DataFrame。"""
import numpy as np
import pandas as pd

from .columns import infer_coordinate_columns
from .outlier import apply_outlier_detection
from .gap_fill import apply_gap_filling
from .filtering import apply_filter


def _frame_values(df, frame_col):
    if frame_col in df.columns:
        vals = pd.to_numeric(df[frame_col], errors="coerce").to_numpy(dtype=float)
        if np.isfinite(vals).all():
            return vals
    return np.arange(len(df), dtype=float)


def postprocess_wide_df(df, params):
    """
    对宽表格式的 3D 姿态 DataFrame 执行三步后处理。

    参数
    ----
    df : pd.DataFrame
        宽表格式，列为 frame_id + 各关节点 _x/_y/_z。
    params : object
        需有属性 FPS, FRAME_COL, OUTLIER, INTERPOLATION, FILTER。

    返回
    ----
    processed_df : pd.DataFrame
        处理后的 DataFrame，结构同输入。
    info : dict
        包含 outlier/interpolation 统计信息的字典。
    """
    frame_col = getattr(params, "FRAME_COL", "frame_id")

    coord_cols = infer_coordinate_columns(df, frame_col=frame_col)
    if not coord_cols:
        raise ValueError("未识别到坐标列，请检查列名是否为 点名_x/点名_y/点名_z。")

    # 1. 异常值处理
    cleaned_df, outlier_mask_df, outlier_detail = apply_outlier_detection(df, coord_cols, params)

    # 2. 短缺失插值
    frame_values = _frame_values(df, frame_col)
    interp_df, filled_counts = apply_gap_filling(cleaned_df, coord_cols, frame_values, params)

    # 3. 低通滤波
    filtered_df = apply_filter(interp_df, coord_cols, params)

    info = {
        "outlier_total": int(outlier_mask_df.sum().sum()),
        "outlier_detail": outlier_detail,
        "interp_total_filled": int(sum(filled_counts.values())),
        "interp_detail": filled_counts,
    }

    return filtered_df, info
