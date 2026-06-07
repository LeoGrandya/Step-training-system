import numpy as np
import pandas as pd


def compute_com_acceleration(df: pd.DataFrame) -> pd.Series:
    dv = df["com_speed_mps"].diff()
    dt = df["time_s"].diff()
    acc = dv / dt
    return acc.replace([np.inf, -np.inf], np.nan).fillna(0.0).rename("com_acceleration_mps2")
