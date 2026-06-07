import numpy as np
import pandas as pd


def compute_com_speed(df: pd.DataFrame) -> pd.Series:
    dx = df["com_x"].diff()
    dy = df["com_y"].diff()
    dz = df["com_z"].diff()
    dt = df["time_s"].diff()

    speed = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2) / dt
    return speed.replace([np.inf, -np.inf], np.nan).fillna(0.0).rename("com_speed_mps")
