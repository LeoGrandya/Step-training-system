import csv
import os
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor

import cv2
import mediapipe as mp
import numpy as np

from pose3d_pkg.detection.common import (
    ensure_parent,
    get_connections_by_format,
    get_joint_names_by_format,
    get_video_fps,
    normalize_output_format,
    write_empty_pose_rows,
    write_pose_rows,
    write_pose2d_header,
)
from pose3d_pkg.io.video_reader import StereoVideoReader


DETECTOR_METHOD = "mediapipe"
LEFT_HEEL_IDX = 29
RIGHT_HEEL_IDX = 30
LEFT_FOOT_INDEX_IDX = 31
RIGHT_FOOT_INDEX_IDX = 32
LEFT_HIP_IDX = 23
RIGHT_HIP_IDX = 24
LEFT_SHOULDER_IDX = 11
RIGHT_SHOULDER_IDX = 12



def _use_gpu_delegate() -> bool:
    raw = os.environ.get("POSE2D_GPU", "1").strip().lower()
    return raw not in ("0", "false", "no")


def create_pose_landmarker(
    model_path: str,
    min_pose_detection_confidence: float = 0.5,
    min_pose_presence_confidence: float = 0.5,
    min_tracking_confidence: float = 0.5,
    num_poses: int = 1,
):
    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    def _build_options(delegate):
        return PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path, delegate=delegate),
            running_mode=VisionRunningMode.VIDEO,
            num_poses=num_poses,
            min_pose_detection_confidence=min_pose_detection_confidence,
            min_pose_presence_confidence=min_pose_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
            output_segmentation_masks=False,
        )

    if _use_gpu_delegate():
        try:
            return PoseLandmarker.create_from_options(_build_options(BaseOptions.Delegate.GPU))
        except Exception as exc:
            print(f"警告: MediaPipe GPU 初始化失败，回退 CPU: {exc}")

    return PoseLandmarker.create_from_options(_build_options(BaseOptions.Delegate.CPU))



def bgr_to_mp_image(frame_bgr):
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)



def _clip_xy(xy):
    return [float(np.clip(xy[0], 0.0, 1.0)), float(np.clip(xy[1], 0.0, 1.0))]



def _safe_min(*vals, default=0.0):
    nums = []
    for v in vals:
        try:
            nums.append(float(v))
        except Exception:
            pass
    return min(nums) if nums else float(default)



def _midpoint(a, b):
    if a is None or b is None:
        return None
    return [(float(a[0]) + float(b[0])) / 2.0, (float(a[1]) + float(b[1])) / 2.0]



def _direction_point(heel_xy, foot_index_xy, extension_ratio: float = 0.60):
    heel = np.array(heel_xy, dtype=np.float64)
    toe = np.array(foot_index_xy, dtype=np.float64)
    vec = toe - heel
    norm = float(np.linalg.norm(vec))
    if norm < 1e-8:
        return _clip_xy(toe)
    direction = toe + extension_ratio * vec
    return _clip_xy(direction.tolist())



def _body_com_point(xy_33):
    hip_mid = _midpoint(xy_33[LEFT_HIP_IDX], xy_33[RIGHT_HIP_IDX])
    shoulder_mid = _midpoint(xy_33[LEFT_SHOULDER_IDX], xy_33[RIGHT_SHOULDER_IDX])
    if hip_mid is not None and shoulder_mid is not None:
        p = 0.60 * np.array(hip_mid, dtype=np.float64) + 0.40 * np.array(shoulder_mid, dtype=np.float64)
        return _clip_xy(p.tolist())
    if hip_mid is not None:
        return _clip_xy(hip_mid)
    if shoulder_mid is not None:
        return _clip_xy(shoulder_mid)
    return None



def convert_mediapipe_pose(pose_result, output_format: str = "mediapipe35"):
    if pose_result is None or not pose_result.pose_landmarks:
        return None, None, None

    output_format = normalize_output_format(output_format, detector_method=DETECTOR_METHOD)
    landmarks = pose_result.pose_landmarks[0]

    xy_33 = []
    visibility_33 = []
    presence_33 = []
    for lm in landmarks:
        xy_33.append([float(lm.x), float(lm.y)])
        visibility_33.append(float(getattr(lm, "visibility", 1.0)))
        presence_33.append(float(getattr(lm, "presence", 1.0)))

    if output_format == "mediapipe33":
        return xy_33, visibility_33, presence_33

    left_fd = _direction_point(xy_33[LEFT_HEEL_IDX], xy_33[LEFT_FOOT_INDEX_IDX])
    right_fd = _direction_point(xy_33[RIGHT_HEEL_IDX], xy_33[RIGHT_FOOT_INDEX_IDX])
    left_fd_vis = _safe_min(visibility_33[LEFT_HEEL_IDX], visibility_33[LEFT_FOOT_INDEX_IDX], default=0.0)
    right_fd_vis = _safe_min(visibility_33[RIGHT_HEEL_IDX], visibility_33[RIGHT_FOOT_INDEX_IDX], default=0.0)
    left_fd_pre = _safe_min(presence_33[LEFT_HEEL_IDX], presence_33[LEFT_FOOT_INDEX_IDX], default=0.0)
    right_fd_pre = _safe_min(presence_33[RIGHT_HEEL_IDX], presence_33[RIGHT_FOOT_INDEX_IDX], default=0.0)

    xy_35 = list(xy_33) + [left_fd, right_fd]
    visibility_35 = list(visibility_33) + [left_fd_vis, right_fd_vis]
    presence_35 = list(presence_33) + [left_fd_pre, right_fd_pre]

    if output_format == "mediapipe35":
        return xy_35, visibility_35, presence_35

    body_com_xy = _body_com_point(xy_33)
    body_com_vis = _safe_min(
        visibility_33[LEFT_HIP_IDX], visibility_33[RIGHT_HIP_IDX],
        visibility_33[LEFT_SHOULDER_IDX], visibility_33[RIGHT_SHOULDER_IDX],
        default=0.0,
    )
    body_com_pre = _safe_min(
        presence_33[LEFT_HIP_IDX], presence_33[RIGHT_HIP_IDX],
        presence_33[LEFT_SHOULDER_IDX], presence_33[RIGHT_SHOULDER_IDX],
        default=0.0,
    )
    return xy_35 + [body_com_xy], visibility_35 + [body_com_vis], presence_35 + [body_com_pre]



def _safe_score(value, default=0.0):
    if value is None:
        return default
    if value == "":
        return default
    try:
        return float(value)
    except Exception:
        return default



def _norm_xy_to_pixel(x: float, y: float, width: int, height: int):
    px = int(round(np.clip(x, 0.0, 1.0) * (width - 1)))
    py = int(round(np.clip(y, 0.0, 1.0) * (height - 1)))
    return px, py



def draw_pose2d_on_frame(
    frame,
    xy,
    visibility,
    presence=None,
    score_threshold=0.20,
    use_presence_for_draw=False,
    draw_skeleton=True,
    draw_labels=False,
    draw_frame_index=False,
    frame_index=None,
    point_radius=4,
    line_thickness=2,
    keypoint_names=None,
    skeleton_edges=None,
):
    canvas = frame.copy()
    h, w = canvas.shape[:2]
    keypoint_names = list(keypoint_names or [])
    skeleton_edges = list(skeleton_edges or [])

    if xy is None:
        if draw_frame_index and frame_index is not None:
            cv2.putText(
                canvas,
                f"frame: {frame_index}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
        return canvas

    def _kp_score(k):
        vis = _safe_score(visibility[k], default=0.0) if visibility is not None else 1.0
        if use_presence_for_draw and presence is not None:
            pre = _safe_score(presence[k], default=0.0)
            return min(vis, pre)
        return vis

    if draw_skeleton:
        for i, j in skeleton_edges:
            if i >= len(xy) or j >= len(xy):
                continue
            if xy[i] is None or xy[j] is None:
                continue

            si = _kp_score(i)
            sj = _kp_score(j)
            if si < score_threshold or sj < score_threshold:
                continue

            pt1 = _norm_xy_to_pixel(xy[i][0], xy[i][1], w, h)
            pt2 = _norm_xy_to_pixel(xy[j][0], xy[j][1], w, h)
            cv2.line(canvas, pt1, pt2, (0, 255, 0), line_thickness, cv2.LINE_AA)

    for k, pt in enumerate(xy):
        if pt is None:
            continue
        score = _kp_score(k)
        if score < score_threshold:
            continue
        center = _norm_xy_to_pixel(pt[0], pt[1], w, h)
        cv2.circle(canvas, center, point_radius, (0, 0, 255), -1, cv2.LINE_AA)
        if draw_labels and k < len(keypoint_names):
            cv2.putText(
                canvas,
                keypoint_names[k],
                (center[0] + 4, center[1] - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 0),
                1,
                cv2.LINE_AA,
            )

    if draw_frame_index and frame_index is not None:
        cv2.putText(
            canvas,
            f"frame: {frame_index}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )

    return canvas



def _create_video_writer(output_path: str, fps: float, size_wh, codec: str = "mp4v"):
    ensure_parent(output_path)
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, size_wh)
    if not writer.isOpened():
        raise RuntimeError(f"无法创建视频写入器: {output_path}")
    return writer



def _make_same_height_for_concat(left_img, right_img):
    h_l, w_l = left_img.shape[:2]
    h_r, w_r = right_img.shape[:2]
    if h_l == h_r:
        return left_img, right_img
    target_h = max(h_l, h_r)
    if h_l != target_h:
        new_w_l = int(round(w_l * (target_h / h_l)))
        left_img = cv2.resize(left_img, (new_w_l, target_h), interpolation=cv2.INTER_LINEAR)
    if h_r != target_h:
        new_w_r = int(round(w_r * (target_h / h_r)))
        right_img = cv2.resize(right_img, (new_w_r, target_h), interpolation=cv2.INTER_LINEAR)
    return left_img, right_img



def extract_pose2d_from_stereo_videos(
    left_video_path: str,
    right_video_path: str,
    model_path: str,
    output_csv_path: str,
    max_frames: Optional[int] = None,
    frame_stride: int = 1,
    show: bool = False,
    filter_cfg=None,
    min_pose_detection_confidence: float = 0.5,
    min_pose_presence_confidence: float = 0.5,
    min_tracking_confidence: float = 0.5,
    num_poses: int = 1,
    output_format: str = "mediapipe35",
    save_vis_video: bool = False,
    vis_left_video_path: Optional[str] = None,
    vis_right_video_path: Optional[str] = None,
    vis_stereo_video_path: Optional[str] = None,
    vis_score_threshold: float = 0.2,
    vis_use_presence_for_draw: bool = False,
    vis_draw_skeleton: bool = True,
    vis_draw_labels: bool = False,
    vis_draw_frame_index: bool = True,
    vis_point_radius: int = 4,
    vis_line_thickness: int = 2,
    vis_codec: str = "mp4v",
    vis_save_left: bool = True,
    vis_save_right: bool = True,
    vis_save_stereo: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None,
):
    output_format = normalize_output_format(output_format, detector_method=DETECTOR_METHOD)
    joint_names = get_joint_names_by_format(output_format)
    skeleton_edges = get_connections_by_format(output_format)

    reader = StereoVideoReader(left_video_path, right_video_path, filter_cfg=filter_cfg)
    reader.print_info()
    fps = get_video_fps(reader.left_info)
    if fps is None or fps <= 1e-6:
        fps = 30.0

    stride = max(1, int(frame_stride or 1))
    total_source_frames = int(reader.left_info.get("frame_count") or 0)
    if total_source_frames <= 0:
        total_source_frames = int(reader.right_info.get("frame_count") or 0)
    expected_processed = (
        (total_source_frames + stride - 1) // stride if total_source_frames > 0 else 0
    )
    if max_frames is not None:
        expected_processed = min(expected_processed, int(max_frames))
    if stride > 1:
        print(f"pose2d 帧采样: stride={stride}, 源 FPS≈{fps:.1f}, 有效 FPS≈{fps / stride:.1f}")

    ensure_parent(output_csv_path)

    left_landmarker = create_pose_landmarker(
        model_path=model_path,
        min_pose_detection_confidence=min_pose_detection_confidence,
        min_pose_presence_confidence=min_pose_presence_confidence,
        min_tracking_confidence=min_tracking_confidence,
        num_poses=num_poses,
    )
    right_landmarker = create_pose_landmarker(
        model_path=model_path,
        min_pose_detection_confidence=min_pose_detection_confidence,
        min_pose_presence_confidence=min_pose_presence_confidence,
        min_tracking_confidence=min_tracking_confidence,
        num_poses=num_poses,
    )

    left_writer = None
    right_writer = None
    stereo_writer = None
    use_parallel_detect = os.environ.get("POSE2D_PARALLEL_DETECT", "1").strip().lower() not in ("0", "false", "no")
    detect_pool = ThreadPoolExecutor(max_workers=2) if use_parallel_detect else None

    try:
        if save_vis_video:
            left_w = int(reader.left_info["width"])
            left_h = int(reader.left_info["height"])
            right_w = int(reader.right_info["width"])
            right_h = int(reader.right_info["height"])

            if vis_save_left and vis_left_video_path:
                left_writer = _create_video_writer(vis_left_video_path, fps, (left_w, left_h), codec=vis_codec)
            if vis_save_right and vis_right_video_path:
                right_writer = _create_video_writer(vis_right_video_path, fps, (right_w, right_h), codec=vis_codec)
            if vis_save_stereo and vis_stereo_video_path:
                stereo_h = max(left_h, right_h)
                stereo_w = int(round(left_w * (stereo_h / left_h))) + int(round(right_w * (stereo_h / right_h)))
                stereo_writer = _create_video_writer(vis_stereo_video_path, fps, (stereo_w, stereo_h), codec=vis_codec)

        processed = 0
        last_progress_pct = -1
        with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            write_pose2d_header(writer)

            while True:
                success, frame_id, left_frame, right_frame = reader.read()
                if not success:
                    break

                if frame_id % stride != 0:
                    continue

                timestamp_ms = int(round((frame_id / fps) * 1000.0))
                h_l, w_l = left_frame.shape[:2]
                h_r, w_r = right_frame.shape[:2]

                left_img = bgr_to_mp_image(left_frame)
                right_img = bgr_to_mp_image(right_frame)
                if detect_pool is not None:
                    left_future = detect_pool.submit(left_landmarker.detect_for_video, left_img, timestamp_ms)
                    right_future = detect_pool.submit(right_landmarker.detect_for_video, right_img, timestamp_ms)
                    left_result = left_future.result()
                    right_result = right_future.result()
                else:
                    left_result = left_landmarker.detect_for_video(left_img, timestamp_ms)
                    right_result = right_landmarker.detect_for_video(right_img, timestamp_ms)

                left_xy, left_vis, left_pre = convert_mediapipe_pose(left_result, output_format=output_format)
                right_xy, right_vis, right_pre = convert_mediapipe_pose(right_result, output_format=output_format)

                if left_xy is None:
                    write_empty_pose_rows(writer, frame_id, timestamp_ms, "left", DETECTOR_METHOD, joint_names=joint_names)
                else:
                    write_pose_rows(
                        writer, frame_id, timestamp_ms, "left", DETECTOR_METHOD,
                        left_xy, w_l, h_l, left_vis, left_pre, joint_names=joint_names,
                    )

                if right_xy is None:
                    write_empty_pose_rows(writer, frame_id, timestamp_ms, "right", DETECTOR_METHOD, joint_names=joint_names)
                else:
                    write_pose_rows(
                        writer, frame_id, timestamp_ms, "right", DETECTOR_METHOD,
                        right_xy, w_r, h_r, right_vis, right_pre, joint_names=joint_names,
                    )

                if save_vis_video or show:
                    left_vis_frame = draw_pose2d_on_frame(
                        left_frame, left_xy, left_vis, presence=left_pre,
                        score_threshold=vis_score_threshold,
                        use_presence_for_draw=vis_use_presence_for_draw,
                        draw_skeleton=vis_draw_skeleton,
                        draw_labels=vis_draw_labels,
                        draw_frame_index=vis_draw_frame_index,
                        frame_index=frame_id,
                        point_radius=vis_point_radius,
                        line_thickness=vis_line_thickness,
                        keypoint_names=joint_names,
                        skeleton_edges=skeleton_edges,
                    )
                    right_vis_frame = draw_pose2d_on_frame(
                        right_frame, right_xy, right_vis, presence=right_pre,
                        score_threshold=vis_score_threshold,
                        use_presence_for_draw=vis_use_presence_for_draw,
                        draw_skeleton=vis_draw_skeleton,
                        draw_labels=vis_draw_labels,
                        draw_frame_index=vis_draw_frame_index,
                        frame_index=frame_id,
                        point_radius=vis_point_radius,
                        line_thickness=vis_line_thickness,
                        keypoint_names=joint_names,
                        skeleton_edges=skeleton_edges,
                    )

                    if left_writer is not None:
                        left_writer.write(left_vis_frame)
                    if right_writer is not None:
                        right_writer.write(right_vis_frame)
                    if stereo_writer is not None:
                        a, b = _make_same_height_for_concat(left_vis_frame, right_vis_frame)
                        stereo_writer.write(np.hstack([a, b]))
                    if show:
                        a, b = _make_same_height_for_concat(left_vis_frame, right_vis_frame)
                        cv2.imshow("pose2d_mediapipe", np.hstack([a, b]))
                        key = cv2.waitKey(1) & 0xFF
                        if key == 27:
                            break

                processed += 1
                if progress_callback is not None and expected_processed > 0:
                    pct = int(processed * 100 / expected_processed)
                    if pct >= last_progress_pct + 1 or processed == expected_processed:
                        last_progress_pct = pct
                        progress_callback(
                            min(1.0, processed / expected_processed),
                            f"2D 姿态检测 {pct}%…",
                        )
                if max_frames is not None and processed >= int(max_frames):
                    break
        if progress_callback is not None:
            progress_callback(1.0, "2D 姿态检测完成")
    finally:
        reader.release()
        left_landmarker.close()
        right_landmarker.close()
        if left_writer is not None:
            left_writer.release()
        if right_writer is not None:
            right_writer.release()
        if stereo_writer is not None:
            stereo_writer.release()
        if show:
            cv2.destroyAllWindows()
        if detect_pool is not None:
            detect_pool.shutdown(wait=True)

    print(f"pose2d_all.csv 已保存到: {output_csv_path}")
    return str(output_csv_path)
