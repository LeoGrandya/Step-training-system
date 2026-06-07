from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np


def _ensure_odd(value: int) -> int:
    value = max(1, int(value))
    if value % 2 == 0:
        value += 1
    return value


def apply_frame_filter(frame: np.ndarray, filter_cfg: Optional[Dict[str, Any]]) -> np.ndarray:
    """对单帧图像做滤波。

    支持的方法：
    - none
    - gaussian
    - median
    - bilateral
    - clahe
    - gaussian_clahe
    """
    if filter_cfg is None:
        return frame
    if not filter_cfg.get('enabled', False):
        return frame

    method = str(filter_cfg.get('method', 'none')).lower()
    out = frame.copy()

    if method in ('none', ''):
        return out

    if method in ('gaussian', 'gaussian_clahe'):
        ksize = _ensure_odd(filter_cfg.get('gaussian_ksize', 5))
        sigma = float(filter_cfg.get('gaussian_sigma', 0.0))
        out = cv2.GaussianBlur(out, (ksize, ksize), sigma)

    if method == 'median':
        ksize = _ensure_odd(filter_cfg.get('median_ksize', 5))
        out = cv2.medianBlur(out, ksize)

    if method == 'bilateral':
        d = int(filter_cfg.get('bilateral_d', 7))
        sigma_color = float(filter_cfg.get('bilateral_sigma_color', 50.0))
        sigma_space = float(filter_cfg.get('bilateral_sigma_space', 50.0))
        out = cv2.bilateralFilter(out, d, sigma_color, sigma_space)

    if method in ('clahe', 'gaussian_clahe'):
        clip_limit = float(filter_cfg.get('clahe_clip_limit', 2.0))
        tile = int(filter_cfg.get('clahe_tile_grid_size', 8))
        lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile, tile))
        l2 = clahe.apply(l)
        lab2 = cv2.merge([l2, a, b])
        out = cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)

    return out


def export_filtered_stereo_videos(
    left_video_path: str,
    right_video_path: str,
    left_output_path: str,
    right_output_path: str,
    filter_cfg: Optional[Dict[str, Any]],
    codec: str = 'mp4v',
) -> None:
    """将滤波后的视频导出，便于用户检查滤波效果。"""
    if filter_cfg is None or not filter_cfg.get('enabled', False):
        return

    left_cap = cv2.VideoCapture(left_video_path)
    right_cap = cv2.VideoCapture(right_video_path)
    if not left_cap.isOpened():
        raise ValueError(f'无法打开左视频: {left_video_path}')
    if not right_cap.isOpened():
        raise ValueError(f'无法打开右视频: {right_video_path}')

    left_w = int(left_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    left_h = int(left_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    right_w = int(right_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    right_h = int(right_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(left_cap.get(cv2.CAP_PROP_FPS) or 30.0)
    fourcc = cv2.VideoWriter_fourcc(*codec)

    Path(left_output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(right_output_path).parent.mkdir(parents=True, exist_ok=True)
    left_writer = cv2.VideoWriter(left_output_path, fourcc, fps, (left_w, left_h))
    right_writer = cv2.VideoWriter(right_output_path, fourcc, fps, (right_w, right_h))

    while True:
        ret_l, frame_l = left_cap.read()
        ret_r, frame_r = right_cap.read()
        if not ret_l or not ret_r:
            break
        left_writer.write(apply_frame_filter(frame_l, filter_cfg))
        right_writer.write(apply_frame_filter(frame_r, filter_cfg))

    left_writer.release()
    right_writer.release()
    left_cap.release()
    right_cap.release()
