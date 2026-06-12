# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

try:
    from scipy.interpolate import PchipInterpolator, Akima1DInterpolator
except Exception:
    PchipInterpolator = None
    Akima1DInterpolator = None


def find_nan_runs(values):
    """返回 NaN 连续区间 [(start, end_exclusive), ...]。"""
    arr = np.asarray(values, dtype=float)
    isnan = np.isnan(arr)
    runs = []
    i = 0
    n = len(arr)
    while i < n:
        if not isnan[i]:
            i += 1
            continue
        start = i
        while i < n and isnan[i]:
            i += 1
        runs.append((start, i))
    return runs


def _interpolate_full(x, y, method="pchip", min_valid_points=4):
    valid = np.isfinite(y)
    if valid.sum() < 2:
        return np.full_like(y, np.nan, dtype=float)

    xv = x[valid]
    yv = y[valid]
    method = method.lower()

    if valid.sum() < min_valid_points:
        method = "linear"

    if method == "linear":
        out = np.interp(x, xv, yv)
        out[x < xv[0]] = np.nan
        out[x > xv[-1]] = np.nan
        return out

    if method == "pchip" and PchipInterpolator is not None:
        f = PchipInterpolator(xv, yv, extrapolate=False)
        return f(x)

    if method in ("akima", "makima") and Akima1DInterpolator is not None:
        try:
            f = Akima1DInterpolator(xv, yv, method=method, extrapolate=False)
        except TypeError:
            f = Akima1DInterpolator(xv, yv)
        return f(x)

    out = np.interp(x, xv, yv)
    out[x < xv[0]] = np.nan
    out[x > xv[-1]] = np.nan
    return out


def fill_short_gaps_series(series, x=None, method="pchip", max_gap_frames=25,
                           min_valid_points=4, inside_only=True):
    y = pd.to_numeric(series, errors="coerce").astype(float).to_numpy()
    n = len(y)
    if x is None:
        x = np.arange(n, dtype=float)
    else:
        x = np.asarray(x, dtype=float)

    full_interp = _interpolate_full(x, y, method=method, min_valid_points=min_valid_points)
    out = y.copy()

    for start, end in find_nan_runs(y):
        gap_len = end - start
        if gap_len > max_gap_frames:
            continue
        if inside_only:
            if start == 0 or end == n:
                continue
            if not (np.isfinite(y[start - 1]) and np.isfinite(y[end])):
                continue
        out[start:end] = full_interp[start:end]

    return pd.Series(out, index=series.index)


def apply_gap_filling(df, coord_cols, frame_values, params):
    cfg = params.INTERPOLATION if hasattr(params, 'INTERPOLATION') else {}
    if not cfg.get("enabled", True):
        return df.copy(), {c: 0 for c in coord_cols}

    filled_df = df.copy()
    filled_counts = {}
    for col in coord_cols:
        before_nan = filled_df[col].isna().sum()
        filled_df[col] = fill_short_gaps_series(
            filled_df[col],
            x=frame_values,
            method=cfg.get("method", "pchip"),
            max_gap_frames=int(cfg.get("max_gap_frames", 25)),
            min_valid_points=int(cfg.get("min_valid_points", 4)),
            inside_only=bool(cfg.get("inside_only", True)),
        )
        after_nan = filled_df[col].isna().sum()
        filled_counts[col] = int(before_nan - after_nan)
    return filled_df, filled_counts
