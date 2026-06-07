"""构建 3D 重建所需的相机/平面几何摘要。

支持两种模式：
1. stereo_triangulation
   - 沿用传统双目三角化
   - 输出左相机坐标系下的 P1 / P2
2. ground_homography_rays
   - 基于地面 4 个控制点建立世界坐标系
   - 使用单应性矩阵得到每台相机的 image->world(XY) 映射
   - 使用 solvePnP 得到每台相机的世界坐标系光心位置
   - 后续 3D 重建采用“两条空间射线最短连线中点”
"""

import json
from pathlib import Path
from typing import Dict

import numpy as np

from pose3d_pkg.calibration.yellow_control_points import build_ground_homography_summary


def load_json(json_path: str) -> dict:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_numpy(data, dtype=np.float64) -> np.ndarray:
    return np.array(data, dtype=dtype)


def build_projection_summary_from_stereo(stereo_params_json: str) -> Dict:
    stereo = load_json(stereo_params_json)

    K1 = to_numpy(stereo["K1"])
    dist1 = to_numpy(stereo.get("dist1", [0, 0, 0, 0, 0]))
    K2 = to_numpy(stereo["K2"])
    dist2 = to_numpy(stereo.get("dist2", [0, 0, 0, 0, 0]))
    R = to_numpy(stereo["R"])
    T = to_numpy(stereo["T"]).reshape(3, 1)

    I = np.eye(3, dtype=np.float64)
    zero = np.zeros((3, 1), dtype=np.float64)

    P1 = K1 @ np.hstack([I, zero])
    P2 = K2 @ np.hstack([R, T])

    baseline = float(np.linalg.norm(T))
    C1 = np.zeros((3, 1), dtype=np.float64)
    C2 = -R.T @ T

    result = {
        "reconstruction_method": "stereo_triangulation",
        "reference_frame": "left_camera",
        "left_camera": {
            "camera_name": "left",
            "K": K1.tolist(),
            "dist": dist1.reshape(-1).tolist(),
            "R": I.tolist(),
            "t": [0.0, 0.0, 0.0],
            "camera_center_world": C1.reshape(-1).tolist(),
            "projection_matrix": P1.tolist(),
        },
        "right_camera": {
            "camera_name": "right",
            "K": K2.tolist(),
            "dist": dist2.reshape(-1).tolist(),
            "R": R.tolist(),
            "t": T.reshape(-1).tolist(),
            "camera_center_world": C2.reshape(-1).tolist(),
            "projection_matrix": P2.tolist(),
        },
        "stereo": {
            "baseline_in_unit": baseline,
            "unit": stereo.get("unit", "meter"),
            "image_size": stereo.get("image_size", None),
        },
    }
    return result


def save_projection_summary_json(result: Dict, save_path: str) -> None:
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def run_build_projection_summary(
    settings: Dict,
    stereo_params_json: str,
    pose_summary_json: str,
    left_video: str,
    right_video: str,
) -> Dict:
    reconstruction_mode = settings.get("pose3d", {}).get("reconstruction_mode", "stereo_triangulation")

    if reconstruction_mode == "ground_homography_rays":
        result = build_ground_homography_summary(
            stereo_params_json=stereo_params_json,
            left_video=left_video,
            right_video=right_video,
            ground_cfg=settings.get("ground_control", {}),
            output_json_path=pose_summary_json,
        )
        return result

    result = build_projection_summary_from_stereo(stereo_params_json)
    save_projection_summary_json(result, pose_summary_json)
    return result
