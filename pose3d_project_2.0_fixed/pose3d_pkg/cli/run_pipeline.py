"""运行时必需。3D 姿态重建管线 CLI：2D 检测 → 三角化 → 可选可视化导出；web_1 pose3d_service 子进程调用。"""
import importlib.util
import re
import time
from pathlib import Path

from pose3d_pkg.calibration.stereo_calibrate import prepare_stereo_params
from pose3d_pkg.io.video_filter import export_filtered_stereo_videos
from pose3d_pkg.io.video_reader import StereoVideoReader
from pose3d_pkg.triangulation.projection import run_build_projection_summary
from pose3d_pkg.triangulation.temporal_filter import temporal_filter_pose3d_abs_csv
from pose3d_pkg.triangulation.triangulate_pose import triangulate_pose_csv
from pose3d_pkg.viz.animate_pose3d import animate_pose3d
from pose3d_pkg.viz.paraview_export import export_paraview_csv_series


def load_settings_from_py(config_path: str):
    config_path = Path(config_path).resolve()
    spec = importlib.util.spec_from_file_location("user_params", config_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    if not hasattr(module, "SETTINGS"):
        raise AttributeError(f"{config_path} 中未找到 SETTINGS")
    return module.SETTINGS


def discover_stereo_pairs(settings):
    input_cfg = settings.get("input", {})

    # 兼容旧版：明确写 video_sources + stereo_pair
    if input_cfg.get("video_sources") and input_cfg.get("stereo_pair"):
        stereo_pair = input_cfg["stereo_pair"]
        video_sources = input_cfg["video_sources"]
        return [{
            "pair_index": 1,
            "pair_name": "pair_001",
            "left_video": str(video_sources[stereo_pair[0]]),
            "right_video": str(video_sources[stereo_pair[1]]),
        }]

    session_dir = Path(input_cfg["session_dir"])
    left_prefix = str(input_cfg.get("left_prefix", "left"))
    right_prefix = str(input_cfg.get("right_prefix", "right"))
    allowed_extensions = {str(ext).lower() for ext in input_cfg.get("allowed_extensions", [".mp4", ".avi", ".mov", ".mkv"])}
    process_pair_indices = input_cfg.get("process_pair_indices")
    if process_pair_indices is not None:
        process_pair_indices = {int(v) for v in process_pair_indices}

    left_regex = re.compile(rf"^{re.escape(left_prefix)}(\d+)$", re.IGNORECASE)
    right_regex = re.compile(rf"^{re.escape(right_prefix)}(\d+)$", re.IGNORECASE)

    left_map = {}
    right_map = {}
    for path in session_dir.iterdir():
        if not path.is_file() or path.suffix.lower() not in allowed_extensions:
            continue
        m_left = left_regex.match(path.stem)
        if m_left:
            left_map[int(m_left.group(1))] = str(path)
            continue
        m_right = right_regex.match(path.stem)
        if m_right:
            right_map[int(m_right.group(1))] = str(path)

    common_ids = sorted(set(left_map.keys()) & set(right_map.keys()))
    if process_pair_indices is not None:
        common_ids = [idx for idx in common_ids if idx in process_pair_indices]

    if not common_ids:
        raise FileNotFoundError(
            f"在 {session_dir} 下未找到成对视频。要求命名格式示例：{left_prefix}1.mp4 / {right_prefix}1.mp4"
        )

    pairs = []
    for idx in common_ids:
        pairs.append({
            "pair_index": int(idx),
            "pair_name": f"pair_{int(idx):03d}",
            "left_video": left_map[idx],
            "right_video": right_map[idx],
        })
    return pairs


def build_pair_output_paths(settings, pair_info):
    outputs = settings["outputs"]
    output_root = Path(outputs["output_dir"])
    pair_dir = output_root / pair_info["pair_name"]
    pair_dir.mkdir(parents=True, exist_ok=True)

    return {
        "pair_dir": pair_dir,
        "pose_summary_json": str(pair_dir / "camera_pose_summary.json"),
        "pose2d_csv": str(pair_dir / "pose2d_all.csv"),
        "pose3d_abs_csv": str(pair_dir / "pose3d_abs.csv"),
        "pose3d_relative_csv": str(pair_dir / "pose3d_relative.csv"),
        "pose3d_abs_filtered_csv": str(pair_dir / "pose3d_abs_filtered.csv"),
        "pose3d_abs_filtered_ground0_csv": str(pair_dir / settings.get("ground_alignment", {}).get("extra_abs_ground_aligned_filename", "pose3d_abs_filtered_zup_ground0.csv")),
        "pose3d_relative_filtered_csv": str(pair_dir / "pose3d_relative_filtered.csv"),
        "pose2d_vis_left_video": str(pair_dir / "pose2d_left_overlay.mp4"),
        "pose2d_vis_right_video": str(pair_dir / "pose2d_right_overlay.mp4"),
        "pose2d_vis_stereo_video": str(pair_dir / "pose2d_stereo_overlay.mp4"),
        "pose3d_animation_path": str(pair_dir / "pose3d_animation.mp4"),
        "paraview_dir": str(pair_dir / "paraview"),
    }


def run_pose2d_detector(settings, left_video: str, right_video: str, pose2d_csv: str, pose2d_vis_paths: dict):
    filter_cfg = settings.get("video_filter", {"enabled": False})
    detector_method = settings["detector"]["method"].lower()
    detector_cfg = settings["detector"]
    outputs_cfg = settings.get("outputs", {})
    pose2d_vis_cfg = settings.get("pose2d_vis", {})
    runtime_cfg = settings.get("_runtime", {}) or {}
    progress_callback = runtime_cfg.get("pose2d_progress_callback")

    if detector_method != "mediapipe":
        raise ValueError("当前工程已精简为只支持 MediaPipe。请在 user_params.py 中保持 detector.method = 'mediapipe'")

    from pose3d_pkg.detection.pose2d_mediapipe import extract_pose2d_from_stereo_videos

    mp_cfg = detector_cfg["mediapipe"]
    return extract_pose2d_from_stereo_videos(
        left_video_path=left_video,
        right_video_path=right_video,
        model_path=mp_cfg["model_path"],
        output_csv_path=pose2d_csv,
        max_frames=detector_cfg["max_frames"],
        frame_stride=int(detector_cfg.get("frame_stride") or 1),
        show=detector_cfg["show_pose2d"],
        min_pose_detection_confidence=mp_cfg["min_pose_detection_confidence"],
        min_pose_presence_confidence=mp_cfg["min_pose_presence_confidence"],
        min_tracking_confidence=mp_cfg["min_tracking_confidence"],
        num_poses=mp_cfg["num_poses"],
        output_format=mp_cfg.get("output_format", "mediapipe35"),
        filter_cfg=filter_cfg,
        save_vis_video=outputs_cfg.get("save_pose2d_vis_video", False),
        vis_left_video_path=pose2d_vis_paths["left"],
        vis_right_video_path=pose2d_vis_paths["right"],
        vis_stereo_video_path=pose2d_vis_paths["stereo"],
        vis_score_threshold=pose2d_vis_cfg.get("score_threshold", 0.20),
        vis_use_presence_for_draw=pose2d_vis_cfg.get("use_presence_for_draw", False),
        vis_draw_skeleton=pose2d_vis_cfg.get("draw_skeleton", True),
        vis_draw_labels=pose2d_vis_cfg.get("draw_labels", False),
        vis_draw_frame_index=pose2d_vis_cfg.get("draw_frame_index", True),
        vis_point_radius=pose2d_vis_cfg.get("point_radius", 4),
        vis_line_thickness=pose2d_vis_cfg.get("line_thickness", 2),
        vis_codec=pose2d_vis_cfg.get("codec", "mp4v"),
        vis_save_left=pose2d_vis_cfg.get("save_left", True),
        vis_save_right=pose2d_vis_cfg.get("save_right", True),
        vis_save_stereo=pose2d_vis_cfg.get("save_stereo", True),
        progress_callback=progress_callback,
    )


def process_one_pair(settings, stereo_params_json: str, pair_info: dict):
    timings: dict[str, float] = {}
    outputs = settings["outputs"]
    filter_cfg = settings.get("video_filter", {"enabled": False})
    temporal_filter_cfg = settings.get("temporal_filter", {"enabled": False})
    temporal_filter_enabled = temporal_filter_cfg.get("enabled", False)
    paraview_cfg = settings.get("paraview_export", {"enabled": False})
    pair_paths = build_pair_output_paths(settings, pair_info)

    left_video = pair_info["left_video"]
    right_video = pair_info["right_video"]

    print("\n" + "=" * 60)
    print(f"开始处理 {pair_info['pair_name']}")
    print(f"left : {left_video}")
    print(f"right: {right_video}")

    if settings["pipeline"].get("run_sync_check", False):
        t0 = time.perf_counter()
        reader = StereoVideoReader(left_video, right_video, filter_cfg=filter_cfg)
        reader.print_info()
        reader.release()
        timings["sync_check_s"] = round(time.perf_counter() - t0, 3)

    if filter_cfg.get("enabled", False) and filter_cfg.get("save_filtered_videos", False):
        t0 = time.perf_counter()
        export_filtered_stereo_videos(
            left_video_path=left_video,
            right_video_path=right_video,
            left_output_path=str(pair_paths["pair_dir"] / "camera1_filtered.mp4"),
            right_output_path=str(pair_paths["pair_dir"] / "camera2_filtered.mp4"),
            filter_cfg=filter_cfg,
        )
        timings["video_filter_export_s"] = round(time.perf_counter() - t0, 3)

    if settings["pipeline"].get("run_build_projection", False):
        t0 = time.perf_counter()
        if settings.get("pose3d", {}).get("reconstruction_mode") == "ground_homography_rays":
            manual_cfg = settings.get("ground_control", {}).get("manual_annotation", {})
            if manual_cfg.get("reuse_saved_points", True) and not manual_cfg.get("force_repick", False):
                print("\n地面控制点模式：若已存在保存点位，则直接读取；若不存在，则弹出窗口手动标定一次并保存。")
            else:
                print("\n地面控制点模式：将弹出左右相机第0帧窗口，请按 TL -> TR -> BR -> BL 顺序手动标定四个点，确认后继续。")
        run_build_projection_summary(
            settings=settings,
            stereo_params_json=stereo_params_json,
            pose_summary_json=pair_paths["pose_summary_json"],
            left_video=left_video,
            right_video=right_video,
        )
        timings["build_projection_s"] = round(time.perf_counter() - t0, 3)

    if settings["pipeline"].get("run_pose2d", False):
        t0 = time.perf_counter()
        run_pose2d_detector(
            settings=settings,
            left_video=left_video,
            right_video=right_video,
            pose2d_csv=pair_paths["pose2d_csv"],
            pose2d_vis_paths={
                "left": pair_paths["pose2d_vis_left_video"],
                "right": pair_paths["pose2d_vis_right_video"],
                "stereo": pair_paths["pose2d_vis_stereo_video"],
            },
        )
        timings["pose2d_s"] = round(time.perf_counter() - t0, 3)
        runtime_cfg = settings.get("_runtime", {}) or {}
        pose3d_progress = runtime_cfg.get("pose3d_progress_callback")
        if callable(pose3d_progress):
            pose3d_progress(0.88, "三角化重建中…")

    if settings["pipeline"].get("run_pose3d", False):
        t0 = time.perf_counter()
        triangulate_pose_csv(
            pose2d_csv_path=pair_paths["pose2d_csv"],
            camera_pose_summary_json=pair_paths["pose_summary_json"],
            output_pose3d_abs_csv_path=pair_paths["pose3d_abs_csv"],
            output_pose3d_relative_csv_path=pair_paths["pose3d_relative_csv"],
            min_visibility=settings["pose3d"]["min_visibility"],
            min_presence=settings["pose3d"]["min_presence"],
            min_reproj_error_px=settings["pose3d"]["min_reproj_error_px"],
            relative_root_mode=settings["pose3d"]["relative_root_mode"],
            root_joint_id=settings["pose3d"].get("root_joint_id"),
            root_joint_name=settings["pose3d"].get("root_joint_name"),
            max_ray_gap_m=settings["pose3d"].get("max_ray_gap_m"),
            axis_signs=settings["pose3d"].get("axis_signs", (1, 1, 1)),
        )
        timings["triangulate_s"] = round(time.perf_counter() - t0, 3)
        runtime_cfg = settings.get("_runtime", {}) or {}
        pose3d_progress = runtime_cfg.get("pose3d_progress_callback")
        if callable(pose3d_progress):
            pose3d_progress(0.94, "时序滤波中…")

        if temporal_filter_enabled:
            t0 = time.perf_counter()
            ground_align_cfg = settings.get("ground_alignment", {})
            temporal_filter_pose3d_abs_csv(
                input_pose3d_abs_csv_path=pair_paths["pose3d_abs_csv"],
                output_pose3d_abs_csv_path=pair_paths["pose3d_abs_filtered_csv"],
                output_pose3d_relative_csv_path=pair_paths["pose3d_relative_filtered_csv"],
                method=temporal_filter_cfg.get("method", "median_then_mean"),
                window_size=temporal_filter_cfg.get("window_size", 5),
                relative_root_mode=settings["pose3d"]["relative_root_mode"],
                root_joint_id=settings["pose3d"].get("root_joint_id"),
                root_joint_name=settings["pose3d"].get("root_joint_name"),
                ground_align_enabled=ground_align_cfg.get("enabled", False),
                ground_align_joint_names=ground_align_cfg.get("joint_names"),
                ground_align_statistic=ground_align_cfg.get("statistic", "mean"),
                ground_align_target_z=ground_align_cfg.get("target_z", 0.0),
                extra_abs_output_csv_path=(
                    pair_paths["pose3d_abs_filtered_ground0_csv"]
                    if ground_align_cfg.get("enabled", False) and ground_align_cfg.get("save_extra_abs_ground_aligned_csv", True)
                    else None
                ),
            )
            timings["temporal_filter_s"] = round(time.perf_counter() - t0, 3)
        if callable(pose3d_progress):
            pose3d_progress(1.0, "三维姿态重建完成")

        if paraview_cfg.get("enabled", False):
            t0 = time.perf_counter()
            paraview_filtered_source = pair_paths["pose3d_abs_filtered_ground0_csv"] if Path(pair_paths["pose3d_abs_filtered_ground0_csv"]).exists() else pair_paths["pose3d_abs_filtered_csv"]
            paraview_source_csv = paraview_filtered_source if (
                paraview_cfg.get("use_filtered_if_available", True)
                and temporal_filter_enabled
                and Path(paraview_filtered_source).exists()
            ) else pair_paths["pose3d_abs_csv"]
            export_paraview_csv_series(
                pose3d_abs_csv_path=paraview_source_csv,
                output_dir=pair_paths["paraview_dir"],
                root_mode=settings["pose3d"]["relative_root_mode"],
                root_joint_id=settings["pose3d"].get("root_joint_id"),
                root_joint_name=settings["pose3d"].get("root_joint_name"),
                axis_length_m=paraview_cfg.get("axis_length_m"),
                grid_step_m=paraview_cfg.get("grid_step_m", 0.25),
                range_margin_m=paraview_cfg.get("range_margin_m", 0.5),
                include_trajectory_history=paraview_cfg.get("include_trajectory_history", True),
                export_segment_endpoints=paraview_cfg.get("export_segment_endpoints", True),
                frame_prefix=paraview_cfg.get("frame_prefix", "paraview_frame_"),
            )
            timings["paraview_export_s"] = round(time.perf_counter() - t0, 3)

    if settings["pipeline"].get("run_pose3d_animation", False) or outputs.get("save_pose3d_animation", False):
        t0 = time.perf_counter()
        source = outputs["animation_source"]
        if temporal_filter_enabled and Path(pair_paths["pose3d_abs_filtered_csv"]).exists() and Path(pair_paths["pose3d_relative_filtered_csv"]).exists():
            abs_anim_csv = pair_paths["pose3d_abs_filtered_ground0_csv"] if Path(pair_paths["pose3d_abs_filtered_ground0_csv"]).exists() else pair_paths["pose3d_abs_filtered_csv"]
            csv_path = pair_paths["pose3d_relative_filtered_csv"] if source == "relative" else abs_anim_csv
        else:
            csv_path = pair_paths["pose3d_relative_csv"] if source == "relative" else pair_paths["pose3d_abs_csv"]

        animate_pose3d(
            pose3d_csv_path=csv_path,
            source=source,
            save_path=pair_paths["pose3d_animation_path"] if outputs.get("save_pose3d_animation", False) else None,
        )
        timings["pose3d_animation_s"] = round(time.perf_counter() - t0, 3)

    cleanup_map = {
        pair_paths["pose_summary_json"]: outputs.get("save_camera_pose_summary_json", True),
        pair_paths["pose2d_csv"]: outputs.get("save_pose2d_csv", True),
        pair_paths["pose3d_abs_csv"]: outputs.get("save_pose3d_abs_csv", True),
        pair_paths["pose3d_relative_csv"]: outputs.get("save_pose3d_relative_csv", True),
        pair_paths["pose3d_abs_filtered_csv"]: outputs.get("save_pose3d_abs_filtered_csv", True),
        pair_paths["pose3d_abs_filtered_ground0_csv"]: settings.get("ground_alignment", {}).get("save_extra_abs_ground_aligned_csv", True),
        pair_paths["pose3d_relative_filtered_csv"]: outputs.get("save_pose3d_relative_filtered_csv", True),
    }
    for path_str, keep in cleanup_map.items():
        p = Path(path_str)
        if p.exists() and not keep:
            p.unlink()

    print(f"\n{pair_info['pair_name']} 处理完成。")
    artifact_labels = [
        ("camera_pose_summary.json", pair_paths["pose_summary_json"]),
        ("pose2d_all.csv", pair_paths["pose2d_csv"]),
        ("pose3d_abs.csv", pair_paths["pose3d_abs_csv"]),
        ("pose3d_relative.csv", pair_paths["pose3d_relative_csv"]),
        ("pose3d_abs_filtered.csv", pair_paths["pose3d_abs_filtered_csv"]),
        ("pose3d_abs_filtered_zup_ground0.csv", pair_paths["pose3d_abs_filtered_ground0_csv"]),
        ("pose3d_relative_filtered.csv", pair_paths["pose3d_relative_filtered_csv"]),
        ("ParaView目录", pair_paths["paraview_dir"]),
    ]
    existing = [(label, path_str) for label, path_str in artifact_labels if Path(path_str).exists()]
    print(f"产物数: {len(existing)}")
    for label, path_str in existing:
        print(f"{label}: {path_str}")
    return timings


def main(config_path: str | None = None, settings: dict | None = None):
    if settings is None:
        if config_path is None:
            config_path = str(Path(__file__).resolve().parents[1] / "user_params.py")
        settings = load_settings_from_py(config_path)
    stereo_params_json = prepare_stereo_params(settings)
    pairs = discover_stereo_pairs(settings)

    pair_timings: dict[str, dict[str, float]] = {}
    print(f"检测到 {len(pairs)} 对双目视频。")
    for pair_info in pairs:
        pair_timings[pair_info["pair_name"]] = process_one_pair(
            settings=settings,
            stereo_params_json=stereo_params_json,
            pair_info=pair_info,
        )

    print("\n全部流程完成。")
    print(f"detector: {settings['detector']['method']}")
    print(f"stereo_params_json: {stereo_params_json}")
    return pair_timings


if __name__ == "__main__":
    main()
