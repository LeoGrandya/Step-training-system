import numpy as np
import pandas as pd


def _extract_joint(df: pd.DataFrame, joint_name: str) -> pd.DataFrame:
    sub = df[df["joint_name"] == joint_name][["frame_id", "x", "y", "z"]].copy()
    sub = sub.rename(columns={"x": f"{joint_name}_x", "y": f"{joint_name}_y", "z": f"{joint_name}_z"})
    return sub


def build_com_table(df: pd.DataFrame) -> pd.DataFrame:
    frames = pd.DataFrame({"frame_id": sorted(df["frame_id"].unique())})

    body_com = _extract_joint(df, "body_com")
    pelvis = _extract_joint(df, "pelvis")
    left_hip = _extract_joint(df, "left_hip")
    right_hip = _extract_joint(df, "right_hip")

    out = frames.merge(body_com, on="frame_id", how="left")
    out = out.merge(pelvis, on="frame_id", how="left")
    out = out.merge(left_hip, on="frame_id", how="left")
    out = out.merge(right_hip, on="frame_id", how="left")

    out["com_x"] = out["body_com_x"]
    out["com_y"] = out["body_com_y"]
    out["com_z"] = out["body_com_z"]

    pelvis_mask = out["com_x"].isna() & out["pelvis_x"].notna()
    out.loc[pelvis_mask, "com_x"] = out.loc[pelvis_mask, "pelvis_x"]
    out.loc[pelvis_mask, "com_y"] = out.loc[pelvis_mask, "pelvis_y"]
    out.loc[pelvis_mask, "com_z"] = out.loc[pelvis_mask, "pelvis_z"]

    hip_mask = (
        out["com_x"].isna()
        & out["left_hip_x"].notna()
        & out["right_hip_x"].notna()
    )
    out.loc[hip_mask, "com_x"] = (out.loc[hip_mask, "left_hip_x"] + out.loc[hip_mask, "right_hip_x"]) / 2.0
    out.loc[hip_mask, "com_y"] = (out.loc[hip_mask, "left_hip_y"] + out.loc[hip_mask, "right_hip_y"]) / 2.0
    out.loc[hip_mask, "com_z"] = (out.loc[hip_mask, "left_hip_z"] + out.loc[hip_mask, "right_hip_z"]) / 2.0

    return out[["frame_id", "com_x", "com_y", "com_z"]]
