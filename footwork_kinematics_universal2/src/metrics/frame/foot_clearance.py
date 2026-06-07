import numpy as np
import pandas as pd


LEFT_CANDIDATES = ["left_foot_index", "left_heel", "left_ankle"]
RIGHT_CANDIDATES = ["right_foot_index", "right_heel", "right_ankle"]


def _extract_joint_z(df: pd.DataFrame, joint_name: str) -> pd.DataFrame:
    sub = df[df["joint_name"] == joint_name][["frame_id", "z"]].copy()
    return sub.rename(columns={"z": f"{joint_name}_z"})


def _first_available(out: pd.DataFrame, candidates, target_col: str):
    out[target_col] = pd.NA
    for joint in candidates:
        col = f"{joint}_z"
        if col in out.columns:
            mask = out[target_col].isna() & out[col].notna()
            out.loc[mask, target_col] = out.loc[mask, col]


def compute_foot_clearance(long_df: pd.DataFrame, frame_df: pd.DataFrame, ground_z: float):
    frames = frame_df[["frame_id"]].copy()

    for joint in LEFT_CANDIDATES + RIGHT_CANDIDATES:
        frames = frames.merge(_extract_joint_z(long_df, joint), on="frame_id", how="left")

    _first_available(frames, LEFT_CANDIDATES, "left_foot_z")
    _first_available(frames, RIGHT_CANDIDATES, "right_foot_z")

    frames["left_clearance_m"] = pd.to_numeric(frames["left_foot_z"], errors="coerce") - float(ground_z)
    frames["right_clearance_m"] = pd.to_numeric(frames["right_foot_z"], errors="coerce") - float(ground_z)

    frames["left_clearance_m"] = frames["left_clearance_m"].clip(lower=0.0)
    frames["right_clearance_m"] = frames["right_clearance_m"].clip(lower=0.0)

    return frames[["frame_id", "left_clearance_m", "right_clearance_m"]]
