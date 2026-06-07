from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.animation import FuncAnimation

from pose3d_pkg.detection.common import (
    MEDIAPIPE_33_JOINT_NAMES,
    MEDIAPIPE_35_JOINT_NAMES,
    MEDIAPIPE_36_JOINT_NAMES,
    get_connections_by_format,
)



def load_pose3d_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)



def detect_output_format(df: pd.DataFrame) -> str:
    names = df[["joint_id", "joint_name"]].drop_duplicates().sort_values("joint_id")["joint_name"].tolist()
    if names == MEDIAPIPE_36_JOINT_NAMES:
        return "mediapipe36"
    if names == MEDIAPIPE_35_JOINT_NAMES:
        return "mediapipe35"
    if names == MEDIAPIPE_33_JOINT_NAMES:
        return "mediapipe33"
    if names[: len(MEDIAPIPE_35_JOINT_NAMES)] == MEDIAPIPE_35_JOINT_NAMES:
        return "mediapipe35"
    if names[: len(MEDIAPIPE_33_JOINT_NAMES)] == MEDIAPIPE_33_JOINT_NAMES:
        return "mediapipe33"
    return "custom"



def get_valid_xyz_for_frame(df_frame: pd.DataFrame, x_col: str, y_col: str, z_col: str):
    joint_xyz = {}
    for _, row in df_frame.iterrows():
        if int(row["valid"]) != 1:
            continue
        if pd.isna(row[x_col]) or pd.isna(row[y_col]) or pd.isna(row[z_col]):
            continue
        joint_xyz[int(row["joint_id"])] = np.array([row[x_col], row[y_col], row[z_col]], dtype=np.float64)
    return joint_xyz



def compute_axis_limits(df: pd.DataFrame, x_col: str, y_col: str, z_col: str, pad_ratio: float = 0.1):
    valid_df = df[df["valid"] == 1].dropna(subset=[x_col, y_col, z_col])
    if len(valid_df) == 0:
        return (-1, 1), (-1, 1), (-1, 1)
    x_min, x_max = valid_df[x_col].min(), valid_df[x_col].max()
    y_min, y_max = valid_df[y_col].min(), valid_df[y_col].max()
    z_min, z_max = valid_df[z_col].min(), valid_df[z_col].max()
    x_pad = max((x_max - x_min) * pad_ratio, 0.1)
    y_pad = max((y_max - y_min) * pad_ratio, 0.1)
    z_pad = max((z_max - z_min) * pad_ratio, 0.1)
    return (x_min - x_pad, x_max + x_pad), (y_min - y_pad, y_max + y_pad), (z_min - z_pad, z_max + z_pad)



def draw_axes(ax, axis_len=0.5):
    ax.plot([0, axis_len], [0, 0], [0, 0], linewidth=2)
    ax.plot([0, 0], [0, axis_len], [0, 0], linewidth=2)
    ax.plot([0, 0], [0, 0], [0, axis_len], linewidth=2)
    ax.text(axis_len, 0, 0, "X")
    ax.text(0, axis_len, 0, "Y")
    ax.text(0, 0, axis_len, "Z")



def animate_pose3d(pose3d_csv_path: str, source: str = "relative", interval_ms: int = 50, save_path: str | None = None, fps: int = 20):
    df = load_pose3d_csv(pose3d_csv_path)
    if source == "absolute":
        x_col, y_col, z_col = "x", "y", "z"
    else:
        x_col, y_col, z_col = "x_rel", "y_rel", "z_rel"

    output_format = detect_output_format(df)
    connections = get_connections_by_format(output_format) if output_format.startswith("mediapipe") else []

    frame_ids = sorted(df["frame_id"].dropna().astype(int).unique().tolist())
    xlim, ylim, zlim = compute_axis_limits(df, x_col, y_col, z_col)
    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")

    def update(frame_id):
        ax.cla()
        df_frame = df[df["frame_id"] == frame_id]
        joint_xyz = get_valid_xyz_for_frame(df_frame, x_col, y_col, z_col)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_zlim(zlim)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title(f"3D Pose ({source}) - frame {frame_id}")
        draw_axes(ax, axis_len=0.5)
        if joint_xyz:
            pts = np.array(list(joint_xyz.values()))
            ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2], s=20)
        for a, b in connections:
            if a in joint_xyz and b in joint_xyz:
                pa, pb = joint_xyz[a], joint_xyz[b]
                ax.plot([pa[0], pb[0]], [pa[1], pb[1]], [pa[2], pb[2]], linewidth=2)

    ani = FuncAnimation(fig, update, frames=frame_ids, interval=interval_ms, repeat=True)
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        if save_path.suffix.lower() == ".gif":
            ani.save(str(save_path), writer="pillow", fps=fps)
        else:
            ani.save(str(save_path), writer="ffmpeg", fps=fps)
        print(f"动画已保存到: {save_path}")
    plt.show()
