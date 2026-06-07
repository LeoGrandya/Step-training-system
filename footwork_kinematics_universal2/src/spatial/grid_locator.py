import numpy as np
import pandas as pd


FOOT_JOINTS = [
    "left_heel", "right_heel",
    "left_ankle", "right_ankle",
    "left_foot_index", "right_foot_index",
]


def estimate_ground_z(df: pd.DataFrame, fallback: float = 0.0) -> float:
    foot_df = df[df["joint_name"].isin(FOOT_JOINTS)].copy()
    z = pd.to_numeric(foot_df["z"], errors="coerce").dropna()
    if len(z) == 0:
        return float(fallback)
    return float(np.percentile(z.to_numpy(), 5))


def estimate_grid_center_xy(com_table: pd.DataFrame):
    sub = com_table[["com_x", "com_y"]].dropna().head(30)
    if len(sub) == 0:
        return (0.0, 0.0)
    return tuple(sub.mean().to_numpy())


def locate_nine_grid_cell(x, y, center_xy, cell_size=0.9, total_size=2.7):
    cx, cy = center_xy
    half = total_size / 2.0
    x_min = cx - half
    y_min = cy - half

    if not (x_min <= x <= x_min + total_size and y_min <= y <= y_min + total_size):
        return None

    col = int((x - x_min) // cell_size)
    row_from_bottom = int((y - y_min) // cell_size)

    if col < 0 or col > 2 or row_from_bottom < 0 or row_from_bottom > 2:
        return None

    col = 2 - col
    row_from_top = 2 - row_from_bottom
    return row_from_top * 3 + col + 1
