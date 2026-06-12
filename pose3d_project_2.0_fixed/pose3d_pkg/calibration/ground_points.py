import json
from pathlib import Path
from typing import Tuple, Optional

import cv2
import numpy as np


def build_blob_detector(
    min_area: float = 80.0,
    max_area: float = 10000.0,
    min_circularity: float = 0.5,
    min_dist_between_blobs: float = 10.0,
    min_threshold: float = 10.0,
    max_threshold: float = 220.0,
    threshold_step: float = 10.0,
):
    params = cv2.SimpleBlobDetector_Params()
    params.minThreshold = min_threshold
    params.maxThreshold = max_threshold
    params.thresholdStep = threshold_step
    params.filterByArea = True
    params.minArea = min_area
    params.maxArea = max_area
    params.filterByCircularity = True
    params.minCircularity = min_circularity
    params.filterByConvexity = False
    params.filterByInertia = False
    params.filterByColor = False
    params.minDistBetweenBlobs = min_dist_between_blobs
    return cv2.SimpleBlobDetector_create(params)


def create_world_points(
    pattern_size: Tuple[int, int] = (4, 4),
    spacing_x: float = 0.30,
    spacing_y: float = 0.30,
) -> np.ndarray:
    cols, rows = pattern_size
    objp = np.zeros((rows * cols, 3), np.float32)
    idx = 0
    for r in range(rows):
        for c in range(cols):
            objp[idx] = [c * spacing_x, r * spacing_y, 0.0]
            idx += 1
    return objp


def read_frame_at_index(video_path: str, frame_index: int = 0) -> np.ndarray:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_index >= total_frames:
        cap.release()
        raise ValueError(f"frame_index={frame_index} 超出范围，总帧数={total_frames}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise ValueError(f"无法读取视频帧: {video_path}, frame={frame_index}")
    return frame


def detect_circle_grid_points(
    frame: np.ndarray,
    pattern_size: Tuple[int, int] = (4, 4),
    detector=None,
):
    if detector is None:
        detector = build_blob_detector()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    flags = cv2.CALIB_CB_SYMMETRIC_GRID
    found, centers = cv2.findCirclesGrid(
        gray,
        pattern_size,
        flags=flags,
        blobDetector=detector,
    )
    debug_img = frame.copy()
    if not found:
        keypoints = detector.detect(gray)
        key_img = cv2.drawKeypoints(
            frame, keypoints, None, (0, 255, 0), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS
        )
        found, centers = cv2.findCirclesGrid(
            key_img,
            pattern_size,
            flags=flags,
            blobDetector=detector,
        )
        debug_img = key_img.copy()
    if found:
        cv2.drawChessboardCorners(debug_img, pattern_size, centers, found)
    return found, centers, debug_img


def points_to_list(points: np.ndarray):
    return points.reshape(-1, 2).tolist()


def save_ground_points_json(
    save_path: str,
    world_points: np.ndarray,
    left_points: np.ndarray,
    right_points: np.ndarray,
    pattern_size: Tuple[int, int],
    spacing_x: float,
    spacing_y: float,
    left_video: str,
    right_video: str,
    frame_index: int,
):
    data = {
        "pattern_type": "symmetric_circle_grid",
        "pattern_size": {"cols": int(pattern_size[0]), "rows": int(pattern_size[1])},
        "spacing_x_meter": float(spacing_x),
        "spacing_y_meter": float(spacing_y),
        "source": {
            "left_video": left_video,
            "right_video": right_video,
            "frame_index": int(frame_index),
        },
        "world_points": world_points.tolist(),
        "left_image_points": points_to_list(left_points),
        "right_image_points": points_to_list(right_points),
    }
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def detect_ground_points_from_stereo_videos(
    left_video: str,
    right_video: str,
    save_json_path: str,
    frame_index: int = 0,
    pattern_size: Tuple[int, int] = (4, 4),
    spacing_x: float = 0.30,
    spacing_y: float = 0.30,
    blob_cfg: Optional[dict] = None,
    debug_dir: Optional[str] = None,
):
    blob_cfg = blob_cfg or {}
    detector = build_blob_detector(**blob_cfg)

    left_frame = read_frame_at_index(left_video, frame_index)
    right_frame = read_frame_at_index(right_video, frame_index)

    found_l, centers_l, debug_left = detect_circle_grid_points(left_frame, pattern_size, detector)
    found_r, centers_r, debug_right = detect_circle_grid_points(right_frame, pattern_size, detector)

    if not found_l:
        raise RuntimeError("左视频未检测到 4x4 对称圆点阵，请调整地面圆点、画面或 blob 阈值。")
    if not found_r:
        raise RuntimeError("右视频未检测到 4x4 对称圆点阵，请调整地面圆点、画面或 blob 阈值。")

    world_points = create_world_points(pattern_size, spacing_x, spacing_y)
    save_ground_points_json(
        save_json_path,
        world_points,
        centers_l,
        centers_r,
        pattern_size,
        spacing_x,
        spacing_y,
        left_video,
        right_video,
        frame_index,
    )

    if debug_dir is not None:
        debug_dir = Path(debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(debug_dir / "left_ground_points.jpg"), debug_left)
        cv2.imwrite(str(debug_dir / "right_ground_points.jpg"), debug_right)

    return {
        "world_points": world_points,
        "left_image_points": centers_l,
        "right_image_points": centers_r,
    }
