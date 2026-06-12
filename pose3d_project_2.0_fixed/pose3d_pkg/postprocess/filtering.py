# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt, savgol_filter


def contiguous_true_runs(mask):
    runs = []
    i = 0
    n = len(mask)
    while i < n:
        if not mask[i]:
            i += 1
            continue
        start = i
        while i < n and mask[i]:
            i += 1
        runs.append((start, i))
    return runs


def _butter_filter_segment(y, fps, cutoff_hz, order):
    if cutoff_hz <= 0 or cutoff_hz >= fps / 2:
        return y.copy()
    sos = butter(order, cutoff_hz / (fps / 2.0), btype="low", output="sos")
    min_len = max(12, order * 6)
    if len(y) <= min_len:
        return y.copy()
    try:
        return sosfiltfilt(sos, y)
    except ValueError:
        return y.copy()


def _savgol_filter_segment(y, window, polyorder):
    window = int(window)
    if window % 2 == 0:
        window += 1
    if window <= polyorder:
        window = polyorder + 2 + ((polyorder + 2) % 2 == 0)
    if len(y) < window:
        window = len(y) if len(y) % 2 == 1 else len(y) - 1
    if window <= polyorder or window < 3:
        return y.copy()
    return savgol_filter(y, window_length=window, polyorder=polyorder, mode="interp")


def filter_series(series, fps, method="butterworth", cutoff_hz=6.0,
                  butterworth_order=4, savgol_window=19, savgol_polyorder=3):
    y = pd.to_numeric(series, errors="coerce").astype(float).to_numpy()
    out = y.copy()
    finite = np.isfinite(y)
    for start, end in contiguous_true_runs(finite):
        seg = y[start:end]
        if len(seg) < 3:
            continue
        if method == "butterworth":
            out[start:end] = _butter_filter_segment(seg, fps, cutoff_hz, butterworth_order)
        elif method == "savgol":
            out[start:end] = _savgol_filter_segment(seg, savgol_window, savgol_polyorder)
        elif method == "none":
            out[start:end] = seg
        else:
            raise ValueError(f"未知滤波方法: {method}")
    return pd.Series(out, index=series.index)


def apply_filter(df, coord_cols, params):
    cfg = params.FILTER if hasattr(params, 'FILTER') else {}
    if not cfg.get("enabled", True) or cfg.get("method", "butterworth") == "none":
        return df.copy()

    fps = float(getattr(params, "FPS", 100.0))
    method = cfg.get("method", "butterworth").lower()
    filtered_df = df.copy()

    for col in coord_cols:
        filtered_df[col] = filter_series(
            filtered_df[col],
            fps=fps,
            method=method,
            cutoff_hz=float(cfg.get("cutoff_hz", 6.0)),
            butterworth_order=int(cfg.get("butterworth_order", 4)),
            savgol_window=int(cfg.get("savgol_window", 19)),
            savgol_polyorder=int(cfg.get("savgol_polyorder", 3)),
        )
    return filtered_df
