import importlib.util
import time
from pathlib import Path

import pandas as pd

from pose3d_pkg.calibration.stereo_calibrate import prepare_stereo_params
from pose3d_pkg.io.video_filter import export_filtered_stereo_videos
from pose3d_pkg.io.video_reader import StereoVideoReader
from pose3d_pkg.triangulation.projection import run_build_projection_summary
from pose3d_pkg.triangulation.temporal_filter import ground_align_pose3d_abs_csv, export_pose3d_wide_csv
from pose3d_pkg.triangulation.triangulate_pose import triangulate_pose_csv
from pose3d_pkg.viz.paraview_export import export_paraview_csv_series
from pose3d_pkg.postprocess.pipeline import postprocess_wide_df
from pose3d_pkg.calibration.yellow_control_points import build_ground_homography_summary


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
    """遍历 data/<group>/<person>/left|right/ 结构，按同名文件配对。"""
    input_cfg = settings.get("input", {})
    data_root = Path(input_cfg["data_root"])
    groups = input_cfg.get("groups", [])
    allowed_extensions = {
        str(ext).lower()
        for ext in input_cfg.get("allowed_extensions", [".mp4", ".avi", ".mov", ".mkv"])
    }

    pairs = []
    for group_spec in groups:
        group_path = Path(group_spec)
        # 相对路径 → 拼到 data_root 下；绝对路径 → 直接使用
        if not group_path.is_absolute():
            group_path = data_root / group_path

        if not group_path.is_dir():
            print(f"警告：组目录不存在，跳过: {group_path}")
            continue

        group_name = group_path.name  # 用目录名作为输出标识

        stereo_params_json = group_path / "stereo_params.json"

        for person_dir in sorted(group_path.iterdir()):
            if not person_dir.is_dir():
                continue
            person_name = person_dir.name

            left_dir = person_dir / "left"
            right_dir = person_dir / "right"
            if not left_dir.is_dir() or not right_dir.is_dir():
                continue

            for left_file in sorted(left_dir.iterdir()):
                if not left_file.is_file():
                    continue
                if left_file.suffix.lower() not in allowed_extensions:
                    continue

                right_file = right_dir / left_file.name
                if not right_file.is_file():
                    print(
                        f"警告：{group_name}/{person_name} 中 {left_file.name} "
                        f"在 right/ 下无匹配，跳过"
                    )
                    continue

                file_stem = left_file.stem
                pairs.append({
                    "group": group_name,
                    "person": person_name,
                    "file_stem": file_stem,
                    "pair_name": f"{group_name}_{person_name}_{file_stem}",
                    "left_video": str(left_file),
                    "right_video": str(right_file),
                    "stereo_params_json": str(stereo_params_json),
                })

    if not pairs:
        raise FileNotFoundError(
            f"在 {data_root} 下的各组目录中未找到任何成对视频。\n"
            f"期望结构：data/<group>/<person>/left/<video> + data/<group>/<person>/right/<video>"
        )

    return pairs


def build_pair_output_paths(settings, pair_info):
    output_root = Path(settings["input"]["output_root"])
    pair_dir = (
        output_root
        / pair_info["group"]
        / pair_info["person"]
        / pair_info["file_stem"]
    )
    pair_dir.mkdir(parents=True, exist_ok=True)

    return {
        "pair_dir": pair_dir,
        "pose_summary_json": str(pair_dir / "camera_pose_summary.json"),
        "pose2d_csv": str(pair_dir / "pose2d_all.csv"),
        "pose3d_abs_csv": str(pair_dir / "pose3d_abs.csv"),
        "pose3d_relative_csv": str(pair_dir / "pose3d_relative.csv"),
        "pose3d_abs_ground_aligned_csv": str(pair_dir / "pose3d_abs_zup_ground0.csv"),
        "pose3d_wide_csv": str(pair_dir / "pose3d_wide.csv"),
        "pose3d_wide_processed_csv": str(pair_dir / "pose3d_wide_processed.csv"),
        "pose2d_vis_left_video": str(pair_dir / "pose2d_left_overlay.mp4"),
        "pose2d_vis_right_video": str(pair_dir / "pose2d_right_overlay.mp4"),
        "pose2d_vis_stereo_video": str(pair_dir / "pose2d_stereo_overlay.mp4"),
        "paraview_dir": str(pair_dir / "paraview"),
    }


class _PostProcessParams:
    """将 postprocess 配置 dict 包装为属性访问对象，供后处理模块使用。"""

    def __init__(self, pp: dict):
        self.FPS = float(pp.get("fps", 100.0))
        self.FRAME_COL = "frame_id"
        self.FINAL_OUTPUT_NAME = pp.get("final_output_name", "pose3d_wide_processed.csv")
        self.OUTLIER = pp.get("outlier", {})
        self.INTERPOLATION = pp.get("interpolation", {})
        self.FILTER = pp.get("filter", {})


def _build_postprocess_params(postproc_cfg: dict) -> _PostProcessParams:
    return _PostProcessParams(postproc_cfg)


def _pre_calibrate_all_groups(settings, pairs):
    """在正式处理前，按 group 各标定一次地面控制点。

    每个 group 取其第一个 pair 的第0帧，弹出左右窗口手动标定 TL/TR/BR/BL。
    点位保存到 data/<group>/ground_control_points.json，同 group 下所有 pair 共享。
    """
    reconstruction_mode = settings.get("pose3d", {}).get("reconstruction_mode", "")
    if reconstruction_mode != "ground_homography_rays":
        print("当前 reconstruction_mode 非 ground_homography_rays，跳过地面控制点预标定。")
        return

    # 按 group 去重，每个 group 只标一次
    group_first_pairs: dict[str, dict] = {}
    for pair_info in pairs:
        group = pair_info["group"]
        if group not in group_first_pairs:
            group_first_pairs[group] = pair_info

    if not group_first_pairs:
        return

    print(f"\n{'='*60}")
    print(f"地面控制点预标定：共 {len(group_first_pairs)} 个 group")
    print(f"{'='*60}")

    for group_name, pair_info in group_first_pairs.items():
        group_dir = Path(pair_info["stereo_params_json"]).parent  # data/<group>/
        points_json_path = str(group_dir / "ground_control_points.json")

        if Path(points_json_path).exists():
            print(f"  [{group_name}] 标定点位已存在: {points_json_path}，跳过")
            continue

        print(f"\n  [{group_name}] 开始标定，使用 {pair_info['pair_name']} 的第0帧...")

        stereo_params_json = prepare_stereo_params(
            settings, pair_info["stereo_params_json"]
        )

        # 临时设置 group 级别的标定路径
        ground_cfg = settings.setdefault("ground_control", {})
        manual_cfg = ground_cfg.setdefault("manual_annotation", {})
        debug_cfg = ground_cfg.setdefault("debug", {})

        manual_cfg["points_json_path"] = points_json_path
        debug_cfg["debug_dir"] = str(group_dir / "ground_control_debug")

        # 强制标定：不读取已有文件
        manual_cfg["reuse_saved_points"] = False
        manual_cfg["force_repick"] = False
        manual_cfg["save_points_json"] = True

        # 调用标定流程。输出到临时文件，标定完成后删除（只需 points_json 就够了）
        temp_summary_path = str(group_dir / "_temp_calib_summary.json")
        build_ground_homography_summary(
            stereo_params_json=stereo_params_json,
            left_video=pair_info["left_video"],
            right_video=pair_info["right_video"],
            ground_cfg=ground_cfg,
            output_json_path=temp_summary_path,
        )
        # 清理临时文件
        Path(temp_summary_path).unlink(missing_ok=True)

        print(f"  [{group_name}] 标定完成: {points_json_path}")

    print(f"\n{'='*60}")
    print("地面控制点预标定全部完成，开始处理所有 pair...")
    print(f"{'='*60}")


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
    ground_align_enabled = settings.get("ground_alignment", {}).get("enabled", False)
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

        # 为当前 pair 设置输出路径
        # 标定点位存到 group 级别目录，同 group 所有 pair 共享
        ground_cfg = settings.setdefault("ground_control", {})
        manual_cfg = ground_cfg.setdefault("manual_annotation", {})
        debug_cfg = ground_cfg.setdefault("debug", {})
        group_dir = Path(pair_info["stereo_params_json"]).parent  # data/<group>/
        manual_cfg["points_json_path"] = str(group_dir / "ground_control_points.json")
        debug_cfg["debug_dir"] = str(group_dir / "ground_control_debug")
        manual_cfg["reuse_saved_points"] = True
        manual_cfg["force_repick"] = False

        if settings.get("pose3d", {}).get("reconstruction_mode") == "ground_homography_rays":
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
            pose3d_progress(0.94, "地面对齐与后处理中…")

        if ground_align_enabled:
            t0 = time.perf_counter()
            ground_align_cfg = settings.get("ground_alignment", {})
            ground_align_pose3d_abs_csv(
                input_pose3d_abs_csv_path=pair_paths["pose3d_abs_csv"],
                output_pose3d_abs_csv_path=pair_paths["pose3d_abs_ground_aligned_csv"],
                output_pose3d_relative_csv_path=pair_paths["pose3d_relative_csv"],
                relative_root_mode=settings["pose3d"]["relative_root_mode"],
                root_joint_id=settings["pose3d"].get("root_joint_id"),
                root_joint_name=settings["pose3d"].get("root_joint_name"),
                ground_align_enabled=True,
                ground_align_joint_names=ground_align_cfg.get("joint_names"),
                ground_align_statistic=ground_align_cfg.get("statistic", "mean"),
                ground_align_target_z=ground_align_cfg.get("target_z", 0.0),
            )
            timings["ground_align_s"] = round(time.perf_counter() - t0, 3)

            t0 = time.perf_counter()
            export_pose3d_wide_csv(
                input_pose3d_abs_csv_path=pair_paths["pose3d_abs_ground_aligned_csv"],
                output_wide_csv_path=pair_paths["pose3d_wide_csv"],
            )
            timings["wide_export_s"] = round(time.perf_counter() - t0, 3)

            # ---- 数据后处理：异常值 → 插值 → 滤波 ----
            t0 = time.perf_counter()
            postproc_cfg = settings.get("postprocess", {})
            postproc_params = _build_postprocess_params(postproc_cfg)

            wide_df = pd.read_csv(pair_paths["pose3d_wide_csv"])
            processed_df, postproc_info = postprocess_wide_df(wide_df, postproc_params)
            processed_df.to_csv(pair_paths["pose3d_wide_processed_csv"], index=False, encoding="utf-8")
            timings["postprocess_s"] = round(time.perf_counter() - t0, 3)
            print(f"  后处理完成：异常值 {postproc_info['outlier_total']} 个，插值 {postproc_info['interp_total_filled']} 个点")
        if callable(pose3d_progress):
            pose3d_progress(1.0, "三维姿态重建完成")

        if paraview_cfg.get("enabled", False):
            t0 = time.perf_counter()
            paraview_source_csv = pair_paths["pose3d_abs_ground_aligned_csv"] if (
                ground_align_enabled
                and Path(pair_paths["pose3d_abs_ground_aligned_csv"]).exists()
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

    cleanup_map = {
        pair_paths["pose_summary_json"]: outputs.get("save_camera_pose_summary_json", True),
        pair_paths["pose2d_csv"]: outputs.get("save_pose2d_csv", True),
        pair_paths["pose3d_abs_csv"]: outputs.get("save_pose3d_abs_csv", True),
        pair_paths["pose3d_relative_csv"]: outputs.get("save_pose3d_relative_csv", True),
        pair_paths["pose3d_abs_ground_aligned_csv"]: outputs.get("save_pose3d_abs_ground_aligned_csv", True),
        pair_paths["pose3d_wide_csv"]: outputs.get("save_pose3d_wide_csv", True),
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
        ("pose3d_abs_zup_ground0.csv", pair_paths["pose3d_abs_ground_aligned_csv"]),
        ("pose3d_wide.csv", pair_paths["pose3d_wide_csv"]),
        ("pose3d_wide_processed.csv", pair_paths["pose3d_wide_processed_csv"]),
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
    pairs = discover_stereo_pairs(settings)

    pair_timings: dict[str, dict[str, float]] = {}
    print(f"检测到 {len(pairs)} 对双目视频。")

    # 第一步：按 group 预标定地面控制点（video/adult_video1/adult_video2 各一次）
    _pre_calibrate_all_groups(settings, pairs)

    # 第二步：逐对处理
    for pair_info in pairs:
        stereo_params_json = prepare_stereo_params(
            settings, pair_info["stereo_params_json"]
        )
        pair_timings[pair_info["pair_name"]] = process_one_pair(
            settings=settings,
            stereo_params_json=stereo_params_json,
            pair_info=pair_info,
        )

    print("\n全部流程完成。")
    print(f"detector: {settings['detector']['method']}")
    return pair_timings


if __name__ == "__main__":
    main()
