import pandas as pd

from src.spatial.com_selector import build_com_table
from src.spatial.grid_locator import estimate_ground_z, estimate_grid_center_xy, locate_nine_grid_cell
from src.metrics.frame.com_speed import compute_com_speed
from src.metrics.frame.com_acceleration import compute_com_acceleration
from src.metrics.frame.turning_speed import compute_turning_speed
from src.metrics.frame.foot_clearance import compute_foot_clearance
from src.metrics.frame.joint_angles import compute_joint_angles
from src.metrics.frame.joint_extensions import compute_ankle_sagittal_angles, compute_joint_angular_velocities
from src.metrics.frame.motion_change import compute_motion_change_metrics
from src.events.support_detector import detect_support_states
from src.events.unit_segmenter import segment_units


def _extract_joint_xyz(df: pd.DataFrame, joint_name: str) -> pd.DataFrame:
    sub = df[df["joint_name"] == joint_name][["frame_id", "x", "y", "z"]].copy()
    return sub.rename(columns={"x": f"{joint_name}_x", "y": f"{joint_name}_y", "z": f"{joint_name}_z"})


def _build_step_event_columns(frame_df: pd.DataFrame) -> pd.DataFrame:
    """
    基于已有逐帧支撑状态，构造逐帧“落地事件”列。

    计算逻辑：
    - 任一只脚从上一帧 airborne 变为当前帧 support，记 1 次落地。
    - 左右脚分别判断；若同一帧左右脚都落地，则该帧 step_event_count = 2。
    - 不额外引入新的阈值，直接继承 support_detector.py 里的阈值与滞回逻辑。
    """
    out = frame_df.copy()

    if "left_support_state" not in out.columns or "right_support_state" not in out.columns:
        out["left_landing_event"] = 0
        out["right_landing_event"] = 0
        out["step_event_count"] = 0
        return out

    prev_left = out["left_support_state"].shift(1)
    prev_right = out["right_support_state"].shift(1)

    left_landing = prev_left.eq("airborne") & out["left_support_state"].eq("support")
    right_landing = prev_right.eq("airborne") & out["right_support_state"].eq("support")

    out["left_landing_event"] = left_landing.fillna(False).astype(int)
    out["right_landing_event"] = right_landing.fillna(False).astype(int)
    out["step_event_count"] = out["left_landing_event"] + out["right_landing_event"]
    return out


def build_frame_metrics(pose_df: pd.DataFrame, settings: dict) -> pd.DataFrame:
    fps = float(settings.get("fps", 60.0))
    frame_ids = sorted(pose_df["frame_id"].unique())
    frame_df = pd.DataFrame({"frame_id": frame_ids})
    frame_df["time_s"] = frame_df["frame_id"] / fps

    com_df = build_com_table(pose_df)
    frame_df = frame_df.merge(com_df, on="frame_id", how="left")

    for joint in ["left_hip", "right_hip"]:
        frame_df = frame_df.merge(_extract_joint_xyz(pose_df, joint), on="frame_id", how="left")

    ground_z = settings.get("ground_z")
    if ground_z is None:
        ground_z = estimate_ground_z(pose_df)

    clearance_df = compute_foot_clearance(pose_df, frame_df, ground_z)
    angle_df = compute_joint_angles(pose_df, frame_df)

    frame_df = frame_df.merge(clearance_df, on="frame_id", how="left")
    frame_df = frame_df.merge(angle_df, on="frame_id", how="left")

    frame_df["com_speed_mps"] = compute_com_speed(frame_df)
    frame_df["com_acceleration_mps2"] = compute_com_acceleration(frame_df)
    frame_df["turning_speed_deg_s"] = compute_turning_speed(frame_df)

    motion_change_df = compute_motion_change_metrics(frame_df)
    frame_df = frame_df.merge(motion_change_df, on="frame_id", how="left")

    ankle_sagittal_df = compute_ankle_sagittal_angles(pose_df, frame_df)
    frame_df = frame_df.merge(ankle_sagittal_df, on="frame_id", how="left")

    angular_vel_df = compute_joint_angular_velocities(frame_df)
    frame_df = frame_df.merge(angular_vel_df, on="frame_id", how="left")

    center_xy = settings.get("grid", {}).get("center_xy")
    if not center_xy:
        center_xy = estimate_grid_center_xy(frame_df)
    cell_size = float(settings.get("grid", {}).get("cell_size_m", 0.9))
    total_size = float(settings.get("grid", {}).get("total_size_m", 2.7))

    frame_df["com_cell"] = frame_df.apply(
        lambda row: locate_nine_grid_cell(
            row["com_x"], row["com_y"], center_xy, cell_size, total_size
        ) if pd.notna(row["com_x"]) and pd.notna(row["com_y"]) else pd.NA,
        axis=1
    )

    frame_df["phase_label"] = pd.NA
    frame_df["unit_id"] = pd.NA

    frame_df = detect_support_states(frame_df, settings=settings)
    frame_df = _build_step_event_columns(frame_df)
    frame_df = segment_units(frame_df, settings=settings)

    base_cols = [
        "frame_id", "time_s",
        "com_x", "com_y", "com_z", "com_cell",
        "com_speed_mps", "com_horizontal_speed_mps", "com_acceleration_mps2",
        "turning_speed_deg_s", "motion_heading_deg", "motion_turning_speed_deg_s",
        "direction_change_flag", "direction_change_speed_delta_mps",
        "direction_change_speed_change_rate_abs_mps2",
        "left_clearance_m", "right_clearance_m",
        "left_knee_angle_deg", "right_knee_angle_deg",
        "left_ankle_angle_deg", "right_ankle_angle_deg",
        "left_ankle_sagittal_angle_deg", "right_ankle_sagittal_angle_deg",
        "left_ankle_motion_label", "right_ankle_motion_label",
        "left_knee_angular_velocity_deg_s", "right_knee_angular_velocity_deg_s",
        "left_ankle_angular_velocity_deg_s", "right_ankle_angular_velocity_deg_s",
        "left_ankle_sagittal_angular_velocity_deg_s", "right_ankle_sagittal_angular_velocity_deg_s",
        "left_support_state", "right_support_state", "support_mode",
        "left_landing_event", "right_landing_event", "step_event_count",
        "phase_label", "unit_id", "target_cell",
    ]
    existing_cols = [c for c in base_cols if c in frame_df.columns]
    return frame_df[existing_cols].copy()
