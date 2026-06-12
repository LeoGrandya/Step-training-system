# -*- coding: utf-8 -*-
"""
Butterworth 零相位低通滤波器。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from scipy.signal import butter, filtfilt
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


def butterworth_lowpass_filter(
    series: pd.Series,
    fps: float,
    cutoff_hz: float = 8.0,
    order: int = 4,
) -> pd.Series:
    """
    对单列时序做零相位 Butterworth 低通滤波。

    Parameters
    ----------
    series : pd.Series
        输入信号。
    fps : float
        采样率。
    cutoff_hz : float
        截止频率（Hz）。
    order : int
        滤波器阶数。

    Returns
    -------
    pd.Series
        滤波后的信号，NaN 位置保持 NaN。
    """
    s = pd.to_numeric(series, errors="coerce")
    out = pd.Series(np.nan, index=s.index, dtype=float)
    finite = s.dropna()
    if finite.empty:
        return out

    # 临时线性插值以连续运行 filtfilt
    filled = s.interpolate(method="linear", limit_direction="both")
    arr = filled.to_numpy(dtype=float)

    if fps <= 0 or cutoff_hz <= 0:
        return pd.Series(arr, index=s.index, dtype=float)

    if _HAS_SCIPY and len(arr) > max(12, order * 6):
        nyq = 0.5 * fps
        normal_cutoff = min(float(cutoff_hz) / nyq, 0.99)
        try:
            b, a = butter(order, normal_cutoff, btype="low", analog=False)
            filtered = filtfilt(b, a, arr)
            result = pd.Series(filtered, index=s.index, dtype=float)
            # NaN 位置恢复为 NaN
            result[s.isna()] = np.nan
            return result
        except Exception:
            pass

    # 备用方案：居中滚动均值
    window = max(int(round(fps / max(cutoff_hz, 1.0))), 3)
    if window % 2 == 0:
        window += 1
    result = filled.rolling(window=window, center=True, min_periods=1).mean()
    result[s.isna()] = np.nan
    return result


def filter_frame_coordinates(
    frame_df: pd.DataFrame,
    fps: float,
    cutoff_hz: float = 8.0,
    order: int = 4,
    coord_columns: list | None = None,
) -> pd.DataFrame:
    """
    对宽表中所有坐标列做 Butterworth 低通滤波，原地替换。

    Parameters
    ----------
    frame_df : pd.DataFrame
        逐帧宽表。
    fps : float
        采样率。
    cutoff_hz : float
        截止频率。
    order : int
        滤波器阶数。
    coord_columns : list or None
        需要滤波的列名列表。None = 自动选择所有 _x/_y/_z 结尾的列。

    Returns
    -------
    pd.DataFrame
        滤波后的 DataFrame（原地修改）。
    """
    df = frame_df.copy()

    if coord_columns is None:
        coord_columns = [c for c in df.columns if c.endswith("_x") or c.endswith("_y") or c.endswith("_z")]

    for col in coord_columns:
        if col in df.columns:
            df[col] = butterworth_lowpass_filter(df[col], fps, cutoff_hz, order)

    return df
