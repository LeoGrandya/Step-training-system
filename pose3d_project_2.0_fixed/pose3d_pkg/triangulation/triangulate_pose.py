import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pandas as pd

VIRTUAL_JOINT_ORDER = [
    "left_foot_direction",
    "right_foot_direction",
    "body_com",
]



def load_json(json_path: str) -> dict:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)



def load_projection_summary(camera_pose_summary_json: str):
    data = load_json(camera_pose_summary_json)
    method = data.get("reconstruction_method", "stereo_triangulation")

    left = data["left_camera"]
    right = data["right_camera"]

    summary = {
        "method": method,
        "P1": np.array(left["projection_matrix"], dtype=np.float64),
        "P2": np.array(right["projection_matrix"], dtype=np.float64),
        "C1": np.array(left.get("camera_center_world", [0.0, 0.0, 0.0]), dtype=np.float64).reshape(3),
        "C2": np.array(right.get("camera_center_world", [0.0, 0.0, 0.0]), dtype=np.float64).reshape(3),
        "H1": None,
        "H2": None,
    }

    if method == "ground_homography_rays":
        summary["H1"] = np.array(left["homography_image_to_world"], dtype=np.float64)
        summary["H2"] = np.array(right["homography_image_to_world"], dtype=np.float64)

    return summary



def build_pose2d_lookup(df: pd.DataFrame) -> Dict[Tuple[int, str, int], dict]:
    lookup = {}
    for row in df.itertuples(index=False):
        entry = {
            "x_px": getattr(row, "x_px", np.nan),
            "y_px": getattr(row, "y_px", np.nan),
            "detected": getattr(row, "detected", 0),
            "visibility": getattr(row, "visibility", np.nan),
            "presence": getattr(row, "presence", np.nan),
        }
        lookup[(int(getattr(row, "frame_id")), str(getattr(row, "camera_id")), int(getattr(row, "joint_id")))] = entry
    return lookup



def build_joint_table(df: pd.DataFrame) -> List[Tuple[int, str]]:
    joint_df = df[["joint_id", "joint_name"]].drop_duplicates().copy()
    joint_df["joint_id"] = pd.to_numeric(joint_df["joint_id"], errors="coerce")
    joint_df = joint_df.dropna(subset=["joint_id"]).sort_values("joint_id")
    return [(int(row["joint_id"]), str(row["joint_name"])) for _, row in joint_df.iterrows()]



def build_joint_name_to_id(joint_table: List[Tuple[int, str]]) -> Dict[str, int]:
    return {name: jid for jid, name in joint_table}



def is_valid_row(row: Optional[dict], min_visibility=0.5, min_presence=0.5) -> bool:
    if row is None:
        return False
    detected = row.get("detected", 0)
    if pd.isna(detected) or int(detected) != 1:
        return False
    x_px, y_px = row.get("x_px", np.nan), row.get("y_px", np.nan)
    if pd.isna(x_px) or pd.isna(y_px):
        return False
    visibility, presence = row.get("visibility", np.nan), row.get("presence", np.nan)
    if visibility != "" and not pd.isna(visibility) and float(visibility) < min_visibility:
        return False
    if presence != "" and not pd.isna(presence) and float(presence) < min_presence:
        return False
    return True



def triangulate_one_point(P1, P2, pt1, pt2):
    pts1 = np.array(pt1, dtype=np.float64).reshape(2, 1)
    pts2 = np.array(pt2, dtype=np.float64).reshape(2, 1)
    points4d = cv2.triangulatePoints(P1.astype(np.float64), P2.astype(np.float64), pts1, pts2)
    points4d = points4d[:, 0]
    if abs(points4d[3]) < 1e-12:
        return np.array([np.nan, np.nan, np.nan], dtype=np.float64)
    return (points4d[:3] / points4d[3]).astype(np.float64)



def reproject_point(P: np.ndarray, xyz: np.ndarray) -> np.ndarray:
    xyz_h = np.array([xyz[0], xyz[1], xyz[2], 1.0], dtype=np.float64)
    uvw = P @ xyz_h
    if abs(uvw[2]) < 1e-12:
        return np.array([np.nan, np.nan], dtype=np.float64)
    return np.array([uvw[0] / uvw[2], uvw[1] / uvw[2]], dtype=np.float64)



def image_point_to_world_xy(H_img_to_world: np.ndarray, pt_xy) -> np.ndarray:
    pt = np.array([[[float(pt_xy[0]), float(pt_xy[1])]]], dtype=np.float32)
    world = cv2.perspectiveTransform(pt, H_img_to_world.astype(np.float32))
    return world.reshape(2).astype(np.float64)



def closest_midpoint_between_rays(C1: np.ndarray, G1_xy: np.ndarray, C2: np.ndarray, G2_xy: np.ndarray):
    G1 = np.array([G1_xy[0], G1_xy[1], 0.0], dtype=np.float64)
    G2 = np.array([G2_xy[0], G2_xy[1], 0.0], dtype=np.float64)

    d1 = G1 - C1
    d2 = G2 - C2
    n1 = np.linalg.norm(d1)
    n2 = np.linalg.norm(d2)
    if n1 < 1e-12 or n2 < 1e-12:
        return np.array([np.nan, np.nan, np.nan], dtype=np.float64), np.nan

    d1 = d1 / n1
    d2 = d2 / n2

    A = np.column_stack([d1, -d2])
    b = C2 - C1
    try:
        sol, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
        s, t = float(sol[0]), float(sol[1])
    except np.linalg.LinAlgError:
        return np.array([np.nan, np.nan, np.nan], dtype=np.float64), np.nan

    Q1 = C1 + s * d1
    Q2 = C2 + t * d2
    midpoint = (Q1 + Q2) / 2.0
    gap = float(np.linalg.norm(Q1 - Q2))
    return midpoint.astype(np.float64), gap



def resolve_root_joint_id(
    joint_name_to_id: Dict[str, int],
    root_joint_id: int | None = None,
    root_joint_name: str | None = None,
) -> int | None:
    if root_joint_name is not None and str(root_joint_name).strip() != "":
        return joint_name_to_id.get(str(root_joint_name).strip())
    if root_joint_id is not None:
        try:
            return int(root_joint_id)
        except Exception:
            return None
    return None



def _get_valid_xyz(frame_records: Dict[int, dict], joint_name_to_id: Dict[str, int], joint_name: str):
    jid = joint_name_to_id.get(joint_name)
    if jid is None:
        return None
    rec = frame_records.get(jid)
    if rec is None or int(rec.get("valid_abs", 0)) != 1:
        return None
    x, y, z = rec.get("x_abs", np.nan), rec.get("y_abs", np.nan), rec.get("z_abs", np.nan)
    if pd.isna(x) or pd.isna(y) or pd.isna(z):
        return None
    return np.array([float(x), float(y), float(z)], dtype=np.float64)



def _midpoint(a, b):
    if a is None or b is None:
        return None
    return (np.array(a, dtype=np.float64) + np.array(b, dtype=np.float64)) / 2.0



def _first_valid(*pts):
    for p in pts:
        if p is not None:
            return np.array(p, dtype=np.float64)
    return None



def compute_virtual_foot_direction(frame_records, joint_name_to_id, side: str, extension_ratio: float = 0.60):
    heel = _get_valid_xyz(frame_records, joint_name_to_id, f"{side}_heel")
    foot_index = _get_valid_xyz(frame_records, joint_name_to_id, f"{side}_foot_index")
    ankle = _get_valid_xyz(frame_records, joint_name_to_id, f"{side}_ankle")

    if heel is None and foot_index is None:
        return None
    if heel is None:
        return foot_index
    if foot_index is None:
        return ankle if ankle is not None else heel

    vec = foot_index - heel
    norm = float(np.linalg.norm(vec))
    if norm < 1e-8:
        return foot_index
    return foot_index + extension_ratio * vec



def compute_virtual_body_com(frame_records, joint_name_to_id):
    left_hip = _get_valid_xyz(frame_records, joint_name_to_id, "left_hip")
    right_hip = _get_valid_xyz(frame_records, joint_name_to_id, "right_hip")
    hip_mid = _midpoint(left_hip, right_hip)

    left_shoulder = _get_valid_xyz(frame_records, joint_name_to_id, "left_shoulder")
    right_shoulder = _get_valid_xyz(frame_records, joint_name_to_id, "right_shoulder")
    shoulder_mid = _midpoint(left_shoulder, right_shoulder)

    left_foot = _first_valid(
        _get_valid_xyz(frame_records, joint_name_to_id, "left_heel"),
        _get_valid_xyz(frame_records, joint_name_to_id, "left_ankle"),
    )
    right_foot = _first_valid(
        _get_valid_xyz(frame_records, joint_name_to_id, "right_heel"),
        _get_valid_xyz(frame_records, joint_name_to_id, "right_ankle"),
    )
    foot_mid = _midpoint(left_foot, right_foot)

    if hip_mid is not None and shoulder_mid is not None and foot_mid is not None:
        return 0.55 * hip_mid + 0.30 * shoulder_mid + 0.15 * foot_mid
    if hip_mid is not None and shoulder_mid is not None:
        return 0.60 * hip_mid + 0.40 * shoulder_mid
    if hip_mid is not None:
        return hip_mid
    if shoulder_mid is not None:
        return shoulder_mid
    return None



def compute_frame_root(
    frame_records: Dict[int, dict],
    joint_name_to_id: Dict[str, int],
    root_mode: str = "pelvis_midpoint",
    root_joint_id: int | None = None,
    root_joint_name: str | None = None,
):
    if root_mode == "pelvis_midpoint":
        left_id = joint_name_to_id.get("left_hip")
        right_id = joint_name_to_id.get("right_hip")
        left = frame_records.get(left_id) if left_id is not None else None
        right = frame_records.get(right_id) if right_id is not None else None
        if left and right and int(left["valid_abs"]) == 1 and int(right["valid_abs"]) == 1:
            xyz = (
                np.array([left["x_abs"], left["y_abs"], left["z_abs"]], dtype=np.float64)
                + np.array([right["x_abs"], right["y_abs"], right["z_abs"]], dtype=np.float64)
            ) / 2.0
            return xyz

    resolved_root_joint_id = resolve_root_joint_id(
        joint_name_to_id=joint_name_to_id,
        root_joint_id=root_joint_id,
        root_joint_name=root_joint_name,
    )
    if resolved_root_joint_id is not None and resolved_root_joint_id in frame_records:
        r = frame_records[resolved_root_joint_id]
        if int(r["valid_abs"]) == 1:
            return np.array([r["x_abs"], r["y_abs"], r["z_abs"]], dtype=np.float64)

    for joint_id in sorted(frame_records.keys()):
        rec = frame_records[joint_id]
        if rec and int(rec["valid_abs"]) == 1:
            return np.array([rec["x_abs"], rec["y_abs"], rec["z_abs"]], dtype=np.float64)
    return None



def _get_or_create_virtual_ids(original_joint_table: List[Tuple[int, str]]):
    original_name_to_id = {name: jid for jid, name in original_joint_table}
    max_id = max([jid for jid, _ in original_joint_table], default=-1)
    out = {}
    next_id = max_id + 1
    for name in VIRTUAL_JOINT_ORDER:
        if name in original_name_to_id:
            out[name] = int(original_name_to_id[name])
        else:
            out[name] = int(next_id)
            next_id += 1
    return out



def _safe_row_value(row, key):
    if not row:
        return ""
    return row.get(key, "")



def _normalize_axis_signs(axis_signs) -> np.ndarray:
    if axis_signs is None:
        return np.array([1.0, 1.0, 1.0], dtype=np.float64)
    if len(axis_signs) != 3:
        raise ValueError("axis_signs 必须包含 3 个元素，对应 x/y/z 轴方向，例如 (1, 1, -1)")
    vals = np.array([float(v) for v in axis_signs], dtype=np.float64)
    for i, v in enumerate(vals):
        if abs(v) < 1e-12:
            raise ValueError(f"axis_signs 第 {i} 个值不能为 0")
        vals[i] = 1.0 if v > 0 else -1.0
    return vals



def _apply_axis_transform_to_xyz(xyz: np.ndarray, axis_signs: np.ndarray) -> np.ndarray:
    xyz = np.array(xyz, dtype=np.float64).reshape(3)
    if np.isnan(xyz).any():
        return xyz
    return xyz * axis_signs



def triangulate_pose_csv(
    pose2d_csv_path: str,
    camera_pose_summary_json: str,
    output_pose3d_abs_csv_path: str,
    output_pose3d_relative_csv_path: str,
    min_visibility: float = 0.5,
    min_presence: float = 0.5,
    min_reproj_error_px: float | None = None,
    relative_root_mode: str = "pelvis_midpoint",
    root_joint_id: int | None = None,
    root_joint_name: str | None = None,
    max_ray_gap_m: float | None = None,
    axis_signs: tuple[float, float, float] | list[float] | None = None,
):
    df = pd.read_csv(pose2d_csv_path)
    summary = load_projection_summary(camera_pose_summary_json)
    P1, P2 = summary["P1"], summary["P2"]
    method = summary["method"]
    lookup = build_pose2d_lookup(df)
    frame_ids = sorted(df["frame_id"].dropna().astype(int).unique().tolist())
    original_joint_table = build_joint_table(df)
    virtual_ids = _get_or_create_virtual_ids(original_joint_table)
    real_joint_table = [(jid, name) for jid, name in original_joint_table if name not in VIRTUAL_JOINT_ORDER]
    joint_table_extended = sorted(real_joint_table + [(jid, name) for name, jid in virtual_ids.items()], key=lambda x: x[0])
    joint_name_to_id = build_joint_name_to_id(joint_table_extended)
    resolved_root_joint_id = resolve_root_joint_id(joint_name_to_id, root_joint_id=root_joint_id, root_joint_name=root_joint_name)
    axis_signs = _normalize_axis_signs(axis_signs)

    output_pose3d_abs_csv_path = Path(output_pose3d_abs_csv_path)
    output_pose3d_relative_csv_path = Path(output_pose3d_relative_csv_path)
    output_pose3d_abs_csv_path.parent.mkdir(parents=True, exist_ok=True)
    output_pose3d_relative_csv_path.parent.mkdir(parents=True, exist_ok=True)

    abs_header = [
        "frame_id", "joint_id", "joint_name", "x", "y", "z",
        "left_x_px", "left_y_px", "right_x_px", "right_y_px",
        "left_ground_x", "left_ground_y", "right_ground_x", "right_ground_y",
        "left_visibility", "right_visibility", "left_presence", "right_presence",
        "reproj_err_left_px", "reproj_err_right_px", "ray_gap_m", "valid",
    ]
    rel_header = [
        "frame_id", "joint_id", "joint_name", "root_mode", "root_joint_id", "root_joint_name",
        "root_x", "root_y", "root_z",
        "x_rel", "y_rel", "z_rel",
        "x_abs", "y_abs", "z_abs",
        "valid",
    ]

    with open(output_pose3d_abs_csv_path, "w", newline="", encoding="utf-8") as f_abs, open(
        output_pose3d_relative_csv_path, "w", newline="", encoding="utf-8"
    ) as f_rel:
        abs_writer = csv.writer(f_abs)
        rel_writer = csv.writer(f_rel)
        abs_writer.writerow(abs_header)
        rel_writer.writerow(rel_header)

        for frame_id in frame_ids:
            frame_records = {}

            for joint_id, joint_name in real_joint_table:
                left_row = lookup.get((frame_id, "left", joint_id))
                right_row = lookup.get((frame_id, "right", joint_id))

                valid_left = is_valid_row(left_row, min_visibility, min_presence)
                valid_right = is_valid_row(right_row, min_visibility, min_presence)

                left_ground_xy = ["", ""]
                right_ground_xy = ["", ""]
                ray_gap_m = ""

                if valid_left and valid_right:
                    pt1 = (float(left_row["x_px"]), float(left_row["y_px"]))
                    pt2 = (float(right_row["x_px"]), float(right_row["y_px"]))

                    if method == "ground_homography_rays":
                        g1 = image_point_to_world_xy(summary["H1"], pt1)
                        g2 = image_point_to_world_xy(summary["H2"], pt2)
                        left_ground_xy = [float(g1[0]), float(g1[1])]
                        right_ground_xy = [float(g2[0]), float(g2[1])]
                        xyz, ray_gap = closest_midpoint_between_rays(summary["C1"], g1, summary["C2"], g2)
                        ray_gap_m = float(ray_gap) if not np.isnan(ray_gap) else ""
                    else:
                        xyz = triangulate_one_point(P1, P2, pt1, pt2)

                    uv_left = reproject_point(P1, xyz)
                    uv_right = reproject_point(P2, xyz)
                    err_l = float(np.linalg.norm(uv_left - np.array(pt1))) if not np.isnan(uv_left).any() else np.nan
                    err_r = float(np.linalg.norm(uv_right - np.array(pt2))) if not np.isnan(uv_right).any() else np.nan
                    valid_abs = 1

                    if np.isnan(xyz).any():
                        valid_abs = 0
                    if valid_abs == 1:
                        xyz = _apply_axis_transform_to_xyz(xyz, axis_signs)
                    if min_reproj_error_px is not None and (
                        (not np.isnan(err_l) and err_l > min_reproj_error_px)
                        or (not np.isnan(err_r) and err_r > min_reproj_error_px)
                    ):
                        valid_abs = 0
                    if method == "ground_homography_rays" and max_ray_gap_m is not None and ray_gap_m != "" and float(ray_gap_m) > float(max_ray_gap_m):
                        valid_abs = 0
                else:
                    pt1 = (_safe_row_value(left_row, "x_px"), _safe_row_value(left_row, "y_px"))
                    pt2 = (_safe_row_value(right_row, "x_px"), _safe_row_value(right_row, "y_px"))
                    xyz = np.array([np.nan, np.nan, np.nan], dtype=np.float64)
                    err_l, err_r, valid_abs = "", "", 0

                frame_records[joint_id] = {
                    "joint_name": joint_name,
                    "x_abs": float(xyz[0]) if not np.isnan(xyz[0]) else np.nan,
                    "y_abs": float(xyz[1]) if not np.isnan(xyz[1]) else np.nan,
                    "z_abs": float(xyz[2]) if not np.isnan(xyz[2]) else np.nan,
                    "valid_abs": valid_abs,
                }

                abs_writer.writerow([
                    frame_id,
                    joint_id,
                    joint_name,
                    "" if np.isnan(xyz[0]) else float(xyz[0]),
                    "" if np.isnan(xyz[1]) else float(xyz[1]),
                    "" if np.isnan(xyz[2]) else float(xyz[2]),
                    pt1[0], pt1[1], pt2[0], pt2[1],
                    left_ground_xy[0], left_ground_xy[1], right_ground_xy[0], right_ground_xy[1],
                    _safe_row_value(left_row, "visibility"),
                    _safe_row_value(right_row, "visibility"),
                    _safe_row_value(left_row, "presence"),
                    _safe_row_value(right_row, "presence"),
                    "" if pd.isna(err_l) else err_l,
                    "" if pd.isna(err_r) else err_r,
                    ray_gap_m,
                    valid_abs,
                ])

            # 以 3D heel / foot_index 重新计算脚方向点，使其在绝对坐标下更稳定
            for side in ["left", "right"]:
                joint_name = f"{side}_foot_direction"
                joint_id = virtual_ids[joint_name]
                dir_xyz = compute_virtual_foot_direction(frame_records, joint_name_to_id, side=side)
                left_row = lookup.get((frame_id, "left", joint_id))
                right_row = lookup.get((frame_id, "right", joint_id))
                valid_abs = 1 if dir_xyz is not None and not np.isnan(dir_xyz).any() else 0
                frame_records[joint_id] = {
                    "joint_name": joint_name,
                    "x_abs": np.nan if dir_xyz is None else float(dir_xyz[0]),
                    "y_abs": np.nan if dir_xyz is None else float(dir_xyz[1]),
                    "z_abs": np.nan if dir_xyz is None else float(dir_xyz[2]),
                    "valid_abs": valid_abs,
                }
                abs_writer.writerow([
                    frame_id,
                    joint_id,
                    joint_name,
                    "" if dir_xyz is None else float(dir_xyz[0]),
                    "" if dir_xyz is None else float(dir_xyz[1]),
                    "" if dir_xyz is None else float(dir_xyz[2]),
                    _safe_row_value(left_row, "x_px"), _safe_row_value(left_row, "y_px"),
                    _safe_row_value(right_row, "x_px"), _safe_row_value(right_row, "y_px"),
                    "", "", "", "",
                    _safe_row_value(left_row, "visibility"),
                    _safe_row_value(right_row, "visibility"),
                    _safe_row_value(left_row, "presence"),
                    _safe_row_value(right_row, "presence"),
                    "", "", "",
                    valid_abs,
                ])

            body_com_id = virtual_ids["body_com"]
            body_com_xyz = compute_virtual_body_com(frame_records, joint_name_to_id)
            valid_abs = 1 if body_com_xyz is not None and not np.isnan(body_com_xyz).any() else 0
            frame_records[body_com_id] = {
                "joint_name": "body_com",
                "x_abs": np.nan if body_com_xyz is None else float(body_com_xyz[0]),
                "y_abs": np.nan if body_com_xyz is None else float(body_com_xyz[1]),
                "z_abs": np.nan if body_com_xyz is None else float(body_com_xyz[2]),
                "valid_abs": valid_abs,
            }
            abs_writer.writerow([
                frame_id,
                body_com_id,
                "body_com",
                "" if body_com_xyz is None else float(body_com_xyz[0]),
                "" if body_com_xyz is None else float(body_com_xyz[1]),
                "" if body_com_xyz is None else float(body_com_xyz[2]),
                "", "", "", "",
                "", "", "", "",
                "", "", "", "",
                "", "", "",
                valid_abs,
            ])

            root_xyz = compute_frame_root(
                frame_records=frame_records,
                joint_name_to_id=joint_name_to_id,
                root_mode=relative_root_mode,
                root_joint_id=root_joint_id,
                root_joint_name=root_joint_name,
            )

            for joint_id, joint_name in joint_table_extended:
                rec = frame_records[joint_id]
                valid = int(rec["valid_abs"])
                if root_xyz is not None and valid == 1:
                    xyz_abs = np.array([rec["x_abs"], rec["y_abs"], rec["z_abs"]], dtype=np.float64)
                    xyz_rel = xyz_abs - root_xyz
                    root_vals = root_xyz.tolist()
                else:
                    xyz_rel = np.array([np.nan, np.nan, np.nan], dtype=np.float64)
                    root_vals = [np.nan, np.nan, np.nan] if root_xyz is None else root_xyz.tolist()
                    valid = 0 if root_xyz is None else valid

                rel_writer.writerow([
                    frame_id,
                    joint_id,
                    joint_name,
                    relative_root_mode,
                    "" if resolved_root_joint_id is None else resolved_root_joint_id,
                    "" if root_joint_name is None else root_joint_name,
                    "" if np.isnan(root_vals[0]) else float(root_vals[0]),
                    "" if np.isnan(root_vals[1]) else float(root_vals[1]),
                    "" if np.isnan(root_vals[2]) else float(root_vals[2]),
                    "" if np.isnan(xyz_rel[0]) else float(xyz_rel[0]),
                    "" if np.isnan(xyz_rel[1]) else float(xyz_rel[1]),
                    "" if np.isnan(xyz_rel[2]) else float(xyz_rel[2]),
                    "" if np.isnan(rec["x_abs"]) else float(rec["x_abs"]),
                    "" if np.isnan(rec["y_abs"]) else float(rec["y_abs"]),
                    "" if np.isnan(rec["z_abs"]) else float(rec["z_abs"]),
                    valid,
                ])

    print(f"pose3d_abs.csv 已保存到: {output_pose3d_abs_csv_path}")
    print(f"pose3d_relative.csv 已保存到: {output_pose3d_relative_csv_path}")
    return str(output_pose3d_abs_csv_path), str(output_pose3d_relative_csv_path)
