# -*- coding: utf-8 -*-
import re
import pandas as pd

AXIS_RE = re.compile(r"^(?P<point>.+)_(?P<axis>[xyzXYZ])$")


def infer_coordinate_columns(df, frame_col="frame_id"):
    cols = []
    for c in df.columns:
        if c == frame_col:
            continue
        if AXIS_RE.match(c) and pd.api.types.is_numeric_dtype(df[c]):
            cols.append(c)
    return cols
