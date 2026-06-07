import csv
from pathlib import Path
from typing import Dict, List, Tuple

MEDIAPIPE_33_JOINT_NAMES = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]

# 在 MediaPipe 官方 33 点基础上，增加“脚掌/脚尖方向点”两个虚拟点
MEDIAPIPE_35_JOINT_NAMES = MEDIAPIPE_33_JOINT_NAMES + [
    "left_foot_direction",
    "right_foot_direction",
]

# 在 mediapipe35 基础上，再增加一个 3D 近似重心点
MEDIAPIPE_36_JOINT_NAMES = MEDIAPIPE_35_JOINT_NAMES + [
    "body_com",
]

MEDIAPIPE_33_CONNECTIONS = [
    (0, 2), (0, 5),
    (2, 7), (5, 8),
    (9, 10),
    (11, 12),
    (11, 13), (13, 15),
    (15, 17), (15, 19), (15, 21),
    (12, 14), (14, 16),
    (16, 18), (16, 20), (16, 22),
    (11, 23), (12, 24),
    (23, 24),
    (23, 25), (25, 27), (27, 29), (29, 31),
    (24, 26), (26, 28), (28, 30), (30, 32),
    (27, 31), (28, 32),
]

# 将脚方向点连到脚尖点，以便 2D/3D 骨架显示脚朝向
MEDIAPIPE_35_CONNECTIONS = MEDIAPIPE_33_CONNECTIONS + [
    (31, 33),
    (32, 34),
]

# body_com 不额外连线，只作为一个单独参考点显示
MEDIAPIPE_36_CONNECTIONS = list(MEDIAPIPE_35_CONNECTIONS)

JOINT_FORMATS = {
    "mediapipe33": (MEDIAPIPE_33_JOINT_NAMES, MEDIAPIPE_33_CONNECTIONS),
    "mediapipe35": (MEDIAPIPE_35_JOINT_NAMES, MEDIAPIPE_35_CONNECTIONS),
    "mediapipe36": (MEDIAPIPE_36_JOINT_NAMES, MEDIAPIPE_36_CONNECTIONS),
}


def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)



def normalize_output_format(output_format: str | None, detector_method: str | None = None) -> str:
    if output_format is None or str(output_format).strip() == "":
        return "mediapipe35"

    fmt = str(output_format).strip().lower()
    if fmt not in JOINT_FORMATS:
        raise ValueError(f"不支持的 output_format: {output_format}，可选: {list(JOINT_FORMATS.keys())}")
    return fmt



def get_joint_names_by_format(output_format: str) -> List[str]:
    fmt = normalize_output_format(output_format)
    return list(JOINT_FORMATS[fmt][0])



def get_connections_by_format(output_format: str) -> List[Tuple[int, int]]:
    fmt = normalize_output_format(output_format)
    return list(JOINT_FORMATS[fmt][1])



def detect_joint_format(joint_names: List[str]) -> str:
    names = list(joint_names)
    if names == MEDIAPIPE_36_JOINT_NAMES:
        return "mediapipe36"
    if names == MEDIAPIPE_35_JOINT_NAMES:
        return "mediapipe35"
    if names == MEDIAPIPE_33_JOINT_NAMES:
        return "mediapipe33"
    return "custom"



def get_joint_name_to_id(joint_names: List[str]) -> Dict[str, int]:
    return {name: idx for idx, name in enumerate(joint_names)}



def write_pose2d_header(writer: csv.writer) -> None:
    writer.writerow([
        "frame_id",
        "timestamp_ms",
        "camera_id",
        "detector_method",
        "joint_id",
        "joint_name",
        "x_norm",
        "y_norm",
        "x_px",
        "y_px",
        "visibility",
        "presence",
        "detected",
    ])



def write_empty_pose_rows(
    writer: csv.writer,
    frame_id: int,
    timestamp_ms: int,
    camera_id: str,
    detector_method: str,
    joint_names: List[str] | None = None,
) -> None:
    joint_names = list(joint_names or MEDIAPIPE_35_JOINT_NAMES)
    for joint_id, joint_name in enumerate(joint_names):
        writer.writerow([
            frame_id,
            timestamp_ms,
            camera_id,
            detector_method,
            joint_id,
            joint_name,
            "", "", "", "", "", "", 0,
        ])



def write_pose_rows(
    writer: csv.writer,
    frame_id: int,
    timestamp_ms: int,
    camera_id: str,
    detector_method: str,
    keypoints_xy_norm,
    image_width: int,
    image_height: int,
    visibility=None,
    presence=None,
    joint_names: List[str] | None = None,
) -> None:
    joint_names = list(joint_names or MEDIAPIPE_35_JOINT_NAMES)

    for joint_id, joint_name in enumerate(joint_names):
        xy = keypoints_xy_norm[joint_id] if keypoints_xy_norm is not None and joint_id < len(keypoints_xy_norm) else None
        vis = visibility[joint_id] if visibility is not None and joint_id < len(visibility) else ""
        pre = presence[joint_id] if presence is not None and joint_id < len(presence) else ""

        if xy is None:
            writer.writerow([
                frame_id,
                timestamp_ms,
                camera_id,
                detector_method,
                joint_id,
                joint_name,
                "", "", "", "", vis, pre, 0,
            ])
            continue

        x_norm, y_norm = float(xy[0]), float(xy[1])
        x_px = x_norm * image_width
        y_px = y_norm * image_height

        writer.writerow([
            frame_id,
            timestamp_ms,
            camera_id,
            detector_method,
            joint_id,
            joint_name,
            x_norm,
            y_norm,
            x_px,
            y_px,
            vis,
            pre,
            1,
        ])



def get_video_fps(info: dict, default_fps: float = 30.0) -> float:
    fps = float(info.get("fps", 0.0) or 0.0)
    return fps if fps > 1e-6 else default_fps
