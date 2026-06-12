# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd


def _odd_window(window_size):
    w = int(window_size)
    if w < 3:
        w = 3
    if w % 2 == 0:
        w += 1
    return w


def detect_outliers_median_mad(series, window_size=19, mad_k=3.5,
                               use_scaled_mad=True, min_mad=1e-6):
    """
    滑动窗口 median + MAD 异常值检测。
    返回：cleaned_series, outlier_mask, local_median, threshold
    """
    s = pd.to_numeric(series, errors="coerce").astype(float)
    w = _odd_window(window_size)

    local_median = s.rolling(window=w, center=True, min_periods=max(3, w // 2)).median()
    abs_dev = (s - local_median).abs()
    local_mad = abs_dev.rolling(window=w, center=True, min_periods=max(3, w // 2)).median()

    if use_scaled_mad:
        local_mad = local_mad * 1.4826

    local_mad = local_mad.clip(lower=min_mad)
    threshold = mad_k * local_mad

    mask = abs_dev > threshold
    mask = mask.fillna(False)

    cleaned = s.copy()
    cleaned[mask] = np.nan
    return cleaned, mask.astype(bool), local_median, threshold


def apply_outlier_detection(df, coord_cols, params):
    cfg = params.OUTLIER if hasattr(params, 'OUTLIER') else {}
    if not cfg.get("enabled", True):
        mask_df = pd.DataFrame(False, index=df.index, columns=coord_cols)
        return df.copy(), mask_df, {}

    skip = set(cfg.get("skip_columns", []))
    cleaned_df = df.copy()
    mask_df = pd.DataFrame(False, index=df.index, columns=coord_cols)
    detail = {}

    for col in coord_cols:
        if col in skip:
            continue
        cleaned, mask, med, thr = detect_outliers_median_mad(
            df[col],
            window_size=cfg.get("window_size", 19),
            mad_k=cfg.get("mad_k", 3.5),
            use_scaled_mad=cfg.get("use_scaled_mad", True),
            min_mad=cfg.get("min_mad", 1e-6),
        )
        if cfg.get("replace_with_nan", True):
            cleaned_df[col] = cleaned
        mask_df[col] = mask
        detail[col] = {
            "outlier_count": int(mask.sum()),
            "outlier_ratio": float(mask.mean()) if len(mask) else 0.0,
        }

    return cleaned_df, mask_df, detail
