from pathlib import Path

import numpy as np
import pandas as pd

from pose3d_pkg.detection.common import (
    MEDIAPIPE_33_JOINT_NAMES,
    MEDIAPIPE_35_JOINT_NAMES,
    MEDIAPIPE_36_JOINT_NAMES,
    get_connections_by_format,
)
from pose3d_pkg.triangulation.temporal_filter import compute_frame_root_from_abs_frame



def _detect_output_format(df_abs: pd.DataFrame) -> str:
    names = df_abs[["joint_id", "joint_name"]].drop_duplicates().sort_values("joint_id")["joint_name"].tolist()
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



def _safe_float(v, default=None):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default



def _compute_spans(valid_df: pd.DataFrame):
    x_min, x_max = float(valid_df["x"].min()), float(valid_df["x"].max())
    y_min, y_max = float(valid_df["y"].min()), float(valid_df["y"].max())
    z_min, z_max = float(valid_df["z"].min()), float(valid_df["z"].max())
    return x_min, x_max, y_min, y_max, z_min, z_max



def _make_reference_points(valid_df: pd.DataFrame, axis_length_m=None, grid_step_m=0.25, margin_m=0.5):
    x_min, x_max, y_min, y_max, z_min, z_max = _compute_spans(valid_df)
    span_x = max(x_max - x_min, 0.1)
    span_y = max(y_max - y_min, 0.1)
    span_z = max(z_max - z_min, 0.1)
    axis_length = float(axis_length_m) if axis_length_m not in (None, "") else max(span_x, span_y, span_z, 1.5)

    x0 = np.floor((x_min - margin_m) / grid_step_m) * grid_step_m
    x1 = np.ceil((x_max + margin_m) / grid_step_m) * grid_step_m
    y0 = np.floor((y_min - margin_m) / grid_step_m) * grid_step_m
    y1 = np.ceil((y_max + margin_m) / grid_step_m) * grid_step_m

    rows = []
    point_uid = 0
    axis_samples = 61
    for idx, t in enumerate(np.linspace(0.0, axis_length, axis_samples)):
        rows.append({"frame_id": -1, "entity_type": "axis", "point_group": "x_axis", "point_uid": point_uid,
            "point_name": f"x_axis_{idx}", "joint_id": -1, "x": float(t), "y": 0.0, "z": 0.0,
            "point_size": 4, "is_dynamic": 0,
        }); point_uid += 1
        rows.append({"frame_id": -1, "entity_type": "axis", "point_group": "y_axis", "point_uid": point_uid,
            "point_name": f"y_axis_{idx}", "joint_id": -1, "x": 0.0, "y": float(t), "z": 0.0,
            "point_size": 4, "is_dynamic": 0,
        }); point_uid += 1
        rows.append({"frame_id": -1, "entity_type": "axis", "point_group": "z_axis", "point_uid": point_uid,
            "point_name": f"z_axis_{idx}", "joint_id": -1, "x": 0.0, "y": 0.0, "z": float(t),
            "point_size": 4, "is_dynamic": 0,
        }); point_uid += 1

    rows.append({
        "frame_id": -1, "entity_type": "origin", "point_group": "origin", "point_uid": point_uid,
        "point_name": "origin", "joint_id": -1, "x": 0.0, "y": 0.0, "z": 0.0,
        "point_size": 8, "is_dynamic": 0,
    }); point_uid += 1

    xs = np.arange(x0, x1 + 1e-9, grid_step_m)
    ys = np.arange(y0, y1 + 1e-9, grid_step_m)

    for gx in xs:
        for gy in ys:
            rows.append({
                "frame_id": -1, "entity_type": "ground_grid", "point_group": "ground_grid", "point_uid": point_uid,
                "point_name": f"grid_{gx:.2f}_{gy:.2f}", "joint_id": -1,
                "x": float(gx), "y": float(gy), "z": 0.0,
                "point_size": 2, "is_dynamic": 0,
            })
            point_uid += 1

    meta = {
        "axis_length": axis_length,
        "x_range": (x0, x1),
        "y_range": (y0, y1),
        "z_range": (min(0.0, z_min), max(axis_length, z_max)),
    }
    return pd.DataFrame(rows), meta



def _build_root_trajectory(df_abs: pd.DataFrame, root_mode: str, root_joint_id, root_joint_name):
    rows = []
    for frame_id, grp in df_abs.groupby("frame_id", sort=True):
        g = grp.sort_values("joint_id").copy()
        root_xyz = compute_frame_root_from_abs_frame(g, root_mode=root_mode, root_joint_id=root_joint_id, root_joint_name=root_joint_name)
        if root_xyz is None or np.isnan(root_xyz).any():
            continue
        rows.append({
            "frame_id": int(frame_id),
            "entity_type": "trajectory",
            "point_group": "root_trajectory",
            "point_uid": int(frame_id),
            "point_name": f"root_{int(frame_id):06d}",
            "joint_id": -1,
            "x": float(root_xyz[0]),
            "y": float(root_xyz[1]),
            "z": float(root_xyz[2]),
            "point_size": 5,
            "is_dynamic": 1,
        })
    return pd.DataFrame(rows)



def _build_frame_body_points(df_frame: pd.DataFrame):
    rows = []
    for _, row in df_frame.iterrows():
        if int(row.get("valid", 0)) != 1:
            continue
        x = _safe_float(row.get("x"))
        y = _safe_float(row.get("y"))
        z = _safe_float(row.get("z"))
        if x is None or y is None or z is None:
            continue
        point_size = 12 if str(row.get("joint_name", "")) == "body_com" else 10
        rows.append({
            "frame_id": int(row["frame_id"]),
            "entity_type": "body_joint",
            "point_group": "body_joint",
            "point_uid": int(row["joint_id"]),
            "point_name": str(row["joint_name"]),
            "joint_id": int(row["joint_id"]),
            "x": x, "y": y, "z": z,
            "point_size": point_size,
            "is_dynamic": 1,
        })
    return pd.DataFrame(rows)



def _build_segment_endpoint_rows(df_frame: pd.DataFrame, output_format: str):
    connections = get_connections_by_format(output_format) if output_format.startswith("mediapipe") else []
    lookup = {}
    for _, row in df_frame.iterrows():
        if int(row.get("valid", 0)) != 1:
            continue
        if pd.isna(row.get("x")) or pd.isna(row.get("y")) or pd.isna(row.get("z")):
            continue
        lookup[int(row["joint_id"])] = row

    rows = []
    seg_id = 0
    for a, b in connections:
        if a not in lookup or b not in lookup:
            continue
        ra = lookup[a]
        rb = lookup[b]
        segment_name = f"{ra['joint_name']}__{rb['joint_name']}"
        rows.append({
            "frame_id": int(ra["frame_id"]), "segment_id": seg_id, "segment_name": segment_name,
            "point_order": 0, "joint_id": int(ra["joint_id"]), "joint_name": str(ra["joint_name"]),
            "x": float(ra["x"]), "y": float(ra["y"]), "z": float(ra["z"]),
        })
        rows.append({
            "frame_id": int(rb["frame_id"]), "segment_id": seg_id, "segment_name": segment_name,
            "point_order": 1, "joint_id": int(rb["joint_id"]), "joint_name": str(rb["joint_name"]),
            "x": float(rb["x"]), "y": float(rb["y"]), "z": float(rb["z"]),
        })
        seg_id += 1
    return pd.DataFrame(rows)



def export_paraview_csv_series(
    pose3d_abs_csv_path: str,
    output_dir: str,
    root_mode: str = "pelvis_midpoint",
    root_joint_id=None,
    root_joint_name: str | None = None,
    axis_length_m=None,
    grid_step_m: float = 0.25,
    range_margin_m: float = 0.5,
    include_trajectory_history: bool = True,
    export_segment_endpoints: bool = True,
    frame_prefix: str = "paraview_frame_",
):
    pose3d_abs_csv_path = Path(pose3d_abs_csv_path)
    output_dir = Path(output_dir)
    frames_dir = output_dir / "frame_series"
    segments_dir = output_dir / "segment_endpoints_series"
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    if export_segment_endpoints:
        segments_dir.mkdir(parents=True, exist_ok=True)

    df_abs = pd.read_csv(pose3d_abs_csv_path)
    for col in ["x", "y", "z"]:
        df_abs[col] = pd.to_numeric(df_abs[col], errors="coerce")
    df_abs["valid"] = pd.to_numeric(df_abs["valid"], errors="coerce").fillna(0).astype(int)

    valid_df = df_abs[(df_abs["valid"] == 1)].dropna(subset=["x", "y", "z"]).copy()
    if len(valid_df) == 0:
        raise ValueError("pose3d_abs.csv 中没有有效的 3D 点，无法导出 ParaView CSV")

    output_format = _detect_output_format(df_abs)
    reference_df, ref_meta = _make_reference_points(
        valid_df=valid_df,
        axis_length_m=axis_length_m,
        grid_step_m=float(grid_step_m),
        margin_m=float(range_margin_m),
    )
    trajectory_df = _build_root_trajectory(
        df_abs=df_abs,
        root_mode=root_mode,
        root_joint_id=root_joint_id,
        root_joint_name=root_joint_name,
    )

    reference_df.to_csv(output_dir / "reference_points.csv", index=False, encoding="utf-8")
    trajectory_df.to_csv(output_dir / "root_trajectory.csv", index=False, encoding="utf-8")

    frame_ids = sorted(df_abs["frame_id"].dropna().astype(int).unique().tolist())
    for frame_id in frame_ids:
        df_frame = df_abs[df_abs["frame_id"] == frame_id].copy()
        body_df = _build_frame_body_points(df_frame)
        frame_ref = reference_df.copy()
        frame_ref["frame_id"] = int(frame_id)

        parts = [frame_ref, body_df]
        if include_trajectory_history and len(trajectory_df) > 0:
            hist = trajectory_df[trajectory_df["frame_id"] <= frame_id].copy()
            parts.append(hist)

        frame_out = pd.concat([p for p in parts if len(p) > 0], ignore_index=True)
        frame_out.to_csv(frames_dir / f"{frame_prefix}{int(frame_id):06d}.csv", index=False, encoding="utf-8")

        if export_segment_endpoints:
            seg_df = _build_segment_endpoint_rows(df_frame, output_format=output_format)
            seg_df.to_csv(segments_dir / f"segments_{int(frame_id):06d}.csv", index=False, encoding="utf-8")

    readme = f"""ParaView 导出说明

1. 直接打开 frame_series 文件夹下的 {frame_prefix}000000.csv 所在序列，并勾选文件序列。
2. 使用 Table To Points，X= x，Y= y，Z= z。
3. frame_series 里已经把静态坐标轴、地面网格、当前帧人体点、历史轨迹点合并到每一帧 CSV。
4. reference_points.csv 是单独的静态参考数据；root_trajectory.csv 是整段根节点轨迹。
5. segment_endpoints_series 是骨架端点序列，便于后续在 ParaView 中进一步连线。
6. body_com 为近似重心点；left_foot_direction / right_foot_direction 为脚朝向辅助点。

自动估计范围:
- axis_length = {ref_meta['axis_length']:.3f} m
- x_range = {ref_meta['x_range']}
- y_range = {ref_meta['y_range']}
- z_range = {ref_meta['z_range']}
"""
    (output_dir / "PARAVIEW_README.txt").write_text(readme, encoding="utf-8")

    print(f"ParaView CSV 序列已保存到: {output_dir}")
    return str(output_dir)
