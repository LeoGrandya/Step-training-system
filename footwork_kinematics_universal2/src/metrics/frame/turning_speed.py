import numpy as np
import pandas as pd


def _wrap_deg(angle_deg: pd.Series) -> pd.Series:
    return ((angle_deg + 180.0) % 360.0) - 180.0


def compute_turning_speed(df: pd.DataFrame) -> pd.Series:
    required = ["left_hip_x", "left_hip_y", "right_hip_x", "right_hip_y"]
    if not all(c in df.columns for c in required):
        return pd.Series([pd.NA] * len(df), index=df.index, name="turning_speed_deg_s")

    vx = df["right_hip_x"] - df["left_hip_x"]
    vy = df["right_hip_y"] - df["left_hip_y"]
    heading = np.degrees(np.arctan2(vy, vx))
    d_heading = _wrap_deg(pd.Series(heading).diff())
    dt = df["time_s"].diff()
    turning_speed = d_heading / dt
    return turning_speed.replace([np.inf, -np.inf], np.nan).fillna(0.0).rename("turning_speed_deg_s")
