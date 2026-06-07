import numpy as np
import pandas as pd


# ============================================================
# 【阈值可改】踝关节方向标签阈值（单位：deg）
# ------------------------------------------------------------
# 基于矢状面有符号踝角进行方向划分：
# 正值超过阈值 -> dorsiflexion（背屈）
# 负值超过阈值 -> plantarflexion（跖屈）
# 其余 -> neutral（近中立）
# ============================================================
ANKLE_DIRECTION_THRESHOLD_DEG = 2.0


def _extract_joint_xyz(df: pd.DataFrame, joint_name: str) -> pd.DataFrame:
    sub = df[df["joint_name"] == joint_name][["frame_id", "x", "y", "z"]].copy()
    return sub.rename(columns={"x": f"{joint_name}_x", "y": f"{joint_name}_y", "z": f"{joint_name}_z"})


def _sagittal_signed_ankle_angle_deg(knee_y, knee_z, ankle_y, ankle_z, foot_y, foot_z):
    """
    在 Y-Z 矢状面上计算有符号踝角。

    做法：
    1) 取 shank = ankle -> knee, foot = ankle -> foot_index
    2) 在 Y-Z 平面上计算两向量夹角 angle_0_180
    3) 用 90 - angle_0_180 作为方向化踝角：
       - > 0: 背屈（dorsiflexion）
       - < 0: 跖屈（plantarflexion）

    这样把“约 90°”视作近中立位，方便直接解释为背屈/跖屈偏移量。
    """
    shank = np.array([knee_y - ankle_y, knee_z - ankle_z], dtype=float)
    foot = np.array([foot_y - ankle_y, foot_z - ankle_z], dtype=float)

    if not np.isfinite(shank).all() or not np.isfinite(foot).all():
        return np.nan
    n1 = np.linalg.norm(shank)
    n2 = np.linalg.norm(foot)
    if n1 == 0 or n2 == 0:
        return np.nan

    cos_val = np.dot(shank, foot) / (n1 * n2)
    cos_val = np.clip(cos_val, -1.0, 1.0)
    angle = np.degrees(np.arccos(cos_val))
    return 90.0 - angle


def compute_ankle_sagittal_angles(long_df: pd.DataFrame, frame_df: pd.DataFrame) -> pd.DataFrame:
    frames = frame_df[["frame_id"]].copy()
    joints = [
        "left_knee", "left_ankle", "left_foot_index",
        "right_knee", "right_ankle", "right_foot_index",
    ]
    for j in joints:
        frames = frames.merge(_extract_joint_xyz(long_df, j), on="frame_id", how="left")

    left_vals = []
    right_vals = []
    for _, row in frames.iterrows():
        left_vals.append(
            _sagittal_signed_ankle_angle_deg(
                row.get("left_knee_y"), row.get("left_knee_z"),
                row.get("left_ankle_y"), row.get("left_ankle_z"),
                row.get("left_foot_index_y"), row.get("left_foot_index_z"),
            )
        )
        right_vals.append(
            _sagittal_signed_ankle_angle_deg(
                row.get("right_knee_y"), row.get("right_knee_z"),
                row.get("right_ankle_y"), row.get("right_ankle_z"),
                row.get("right_foot_index_y"), row.get("right_foot_index_z"),
            )
        )

    out = pd.DataFrame({"frame_id": frames["frame_id"]})
    out["left_ankle_sagittal_angle_deg"] = pd.to_numeric(pd.Series(left_vals), errors="coerce")
    out["right_ankle_sagittal_angle_deg"] = pd.to_numeric(pd.Series(right_vals), errors="coerce")

    def _label(series: pd.Series) -> pd.Series:
        th = ANKLE_DIRECTION_THRESHOLD_DEG
        result = pd.Series("neutral", index=series.index, dtype=object)
        result = result.mask(series >= th, "dorsiflexion")
        result = result.mask(series <= -th, "plantarflexion")
        result = result.mask(series.isna(), pd.NA)
        return result

    out["left_ankle_motion_label"] = _label(out["left_ankle_sagittal_angle_deg"])
    out["right_ankle_motion_label"] = _label(out["right_ankle_sagittal_angle_deg"])
    return out


def compute_joint_angular_velocities(frame_df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"frame_id": frame_df["frame_id"]})
    if "time_s" not in frame_df.columns:
        for name in [
            "left_knee_angular_velocity_deg_s",
            "right_knee_angular_velocity_deg_s",
            "left_ankle_angular_velocity_deg_s",
            "right_ankle_angular_velocity_deg_s",
            "left_ankle_sagittal_angular_velocity_deg_s",
            "right_ankle_sagittal_angular_velocity_deg_s",
        ]:
            out[name] = pd.NA
        return out

    dt = pd.to_numeric(frame_df["time_s"], errors="coerce").diff()

    def _vel(angle_col: str, out_name: str):
        if angle_col not in frame_df.columns:
            out[out_name] = pd.NA
            return
        angle = pd.to_numeric(frame_df[angle_col], errors="coerce")
        vel = angle.diff() / dt
        vel = vel.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        out[out_name] = vel

    _vel("left_knee_angle_deg", "left_knee_angular_velocity_deg_s")
    _vel("right_knee_angle_deg", "right_knee_angular_velocity_deg_s")
    _vel("left_ankle_angle_deg", "left_ankle_angular_velocity_deg_s")
    _vel("right_ankle_angle_deg", "right_ankle_angular_velocity_deg_s")
    _vel("left_ankle_sagittal_angle_deg", "left_ankle_sagittal_angular_velocity_deg_s")
    _vel("right_ankle_sagittal_angle_deg", "right_ankle_sagittal_angular_velocity_deg_s")
    return out
