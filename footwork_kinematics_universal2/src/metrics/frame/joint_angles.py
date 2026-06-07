import numpy as np
import pandas as pd


def _extract_joint_xyz(df: pd.DataFrame, joint_name: str) -> pd.DataFrame:
    sub = df[df["joint_name"] == joint_name][["frame_id", "x", "y", "z"]].copy()
    return sub.rename(columns={"x": f"{joint_name}_x", "y": f"{joint_name}_y", "z": f"{joint_name}_z"})


def _angle_3d(a, b, c):
    ba = a - b
    bc = c - b
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba == 0 or norm_bc == 0:
        return np.nan
    cos_val = np.dot(ba, bc) / (norm_ba * norm_bc)
    cos_val = np.clip(cos_val, -1.0, 1.0)
    return np.degrees(np.arccos(cos_val))


def _compute_angle_series(df: pd.DataFrame, ja: str, jb: str, jc: str, out_name: str) -> pd.Series:
    values = []
    for _, row in df.iterrows():
        a = np.array([row[f"{ja}_x"], row[f"{ja}_y"], row[f"{ja}_z"]], dtype=float)
        b = np.array([row[f"{jb}_x"], row[f"{jb}_y"], row[f"{jb}_z"]], dtype=float)
        c = np.array([row[f"{jc}_x"], row[f"{jc}_y"], row[f"{jc}_z"]], dtype=float)
        if not np.isfinite(a).all() or not np.isfinite(b).all() or not np.isfinite(c).all():
            values.append(np.nan)
        else:
            values.append(_angle_3d(a, b, c))
    return pd.Series(values, index=df.index, name=out_name)


def compute_joint_angles(long_df: pd.DataFrame, frame_df: pd.DataFrame) -> pd.DataFrame:
    frames = frame_df[["frame_id"]].copy()

    joints = [
        "left_hip", "left_knee", "left_ankle", "left_foot_index",
        "right_hip", "right_knee", "right_ankle", "right_foot_index",
    ]
    for j in joints:
        frames = frames.merge(_extract_joint_xyz(long_df, j), on="frame_id", how="left")

    frames["left_knee_angle_deg"] = _compute_angle_series(
        frames, "left_hip", "left_knee", "left_ankle", "left_knee_angle_deg"
    )
    frames["right_knee_angle_deg"] = _compute_angle_series(
        frames, "right_hip", "right_knee", "right_ankle", "right_knee_angle_deg"
    )
    frames["left_ankle_angle_deg"] = _compute_angle_series(
        frames, "left_knee", "left_ankle", "left_foot_index", "left_ankle_angle_deg"
    )
    frames["right_ankle_angle_deg"] = _compute_angle_series(
        frames, "right_knee", "right_ankle", "right_foot_index", "right_ankle_angle_deg"
    )

    return frames[[
        "frame_id",
        "left_knee_angle_deg",
        "right_knee_angle_deg",
        "left_ankle_angle_deg",
        "right_ankle_angle_deg",
    ]]
