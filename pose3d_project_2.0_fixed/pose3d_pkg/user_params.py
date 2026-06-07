"""统一参数文件。

本版仅保留 MediaPipe，并新增：
1. 在同一 session 下复用同一个 stereo_params.json
2. 自动识别 left1/right1、left2/right2 ... 成对视频
3. 2D 导出默认使用 mediapipe35：官方 33 点 + 左右脚方向点
4. 3D 导出自动增加 body_com 近似重心点
5. ParaView 导出可直接显示脚方向点与重心点
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SESSION_DIR = PROJECT_ROOT / "data/session_001"
OUTPUT_DIR = PROJECT_ROOT / "output/session_001"

SETTINGS = {
    "input": {
        "session_dir": str(SESSION_DIR),
        "left_prefix": "left",
        "right_prefix": "right",
        "allowed_extensions": [".mp4", ".avi", ".mov", ".mkv"],
        "process_pair_indices": None,
    },

    "detector": {
        "method": "mediapipe",
        "person_selection": "highest_conf",
        "max_frames": None,
        "show_pose2d": False,

        "mediapipe": {
            "model_path": str(PROJECT_ROOT / "models/pose_landmarker_full.task"),
            "output_format": "mediapipe35",
            "min_pose_detection_confidence": 0.4,
            "min_pose_presence_confidence": 0.4,
            "min_tracking_confidence": 0.4,
            "num_poses": 1,
        },
    },

    "video_filter": {
        "enabled": False,
        "method": "gaussian",
        "gaussian_ksize": 5,
        "gaussian_sigma": 0.0,
        "median_ksize": 5,
        "bilateral_d": 7,
        "bilateral_sigma_color": 50.0,
        "bilateral_sigma_space": 50.0,
        "clahe_clip_limit": 2.0,
        "clahe_tile_grid_size": 8,
        "save_filtered_videos": False,
    },

    "pose2d_vis": {
        "score_threshold": 0.20,
        "draw_skeleton": True,
        "draw_labels": False,
        "draw_frame_index": True,
        "point_radius": 4,
        "line_thickness": 2,
        "codec": "mp4v",
        "save_left": True,
        "save_right": True,
        "save_stereo": True,
    },

    "stereo": {
        "stereo_mode": "json",
        "stereo_params_json": str(SESSION_DIR / "stereo_params.json"),
        "manual_stereo_params": {
            "K1": [[1200.0, 0.0, 640.0], [0.0, 1200.0, 360.0], [0.0, 0.0, 1.0]],
            "dist1": [[0.0, 0.0, 0.0, 0.0, 0.0]],
            "K2": [[1200.0, 0.0, 640.0], [0.0, 1200.0, 360.0], [0.0, 0.0, 1.0]],
            "dist2": [[0.0, 0.0, 0.0, 0.0, 0.0]],
            "R": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "T": [[-0.25], [0.0], [0.0]],
            "image_size": [1280, 720],
            "unit": "meter",
        },
    },

    "ground_control": {
        "frame_index": 0,
        "distance_m": 2.7,
        "width_m": 2.7,
        "height_m": 2.7,
        "manual_annotation": {
            "reuse_saved_points": True,
            "force_repick": False,
            "use_saved_as_initial_when_repick": True,
            "save_points_json": True,
            "points_json_path": str(OUTPUT_DIR / "ground_control_debug/manual_control_points.json"),
            "display_scale": 1.0,
            "click_radius_px": 30,
            "show_help": True,
            "window_name_prefix": "ground_control_manual",
        },
        "debug": {
            "save_debug_images": True,
            "debug_dir": str(OUTPUT_DIR / "ground_control_debug"),
        },
    },

    "pose3d": {
        "reconstruction_mode": "ground_homography_rays",
        "min_visibility": 0.5,
        "min_presence": 0.5,
        "min_reproj_error_px": None,
        "max_ray_gap_m": 0.30,

        # 默认将 relative / 轨迹 的根节点切到 body_com（近似重心点）
        "relative_root_mode": "joint",
        "root_joint_id": None,
        "root_joint_name": "body_com",

        # 绝对坐标轴方向约定：x=地面横向，y=地面纵向，z=竖直向上为正
        # 当前相机/地面世界系求出的 z 方向与项目期望相反，因此这里默认翻转 z 轴
        "axis_signs": (1, 1, -1),
    },

    "temporal_filter": {
        "enabled": True,
        "method": "median_then_mean",
        "window_size": 5,
    },

    # 将滤波后的绝对 3D 坐标整体平移，使脚部平均高度贴近 z=0
    # 这样生成的 pose3d_abs_filtered.csv 就与 pose3d_abs_filtered_zup_ground0.csv 同格式
    "ground_alignment": {
        "enabled": True,
        "joint_names": [
            "left_heel", "right_heel",
            "left_ankle", "right_ankle",
            "left_foot_index", "right_foot_index",
        ],
        "statistic": "mean",
        "target_z": 0.0,
        # 额外再保存一份同内容别名文件，便于直接给 PyVista / ParaView 使用
        "save_extra_abs_ground_aligned_csv": True,
        "extra_abs_ground_aligned_filename": "pose3d_abs_filtered_zup_ground0.csv",
    },

    "outputs": {
        "output_dir": str(OUTPUT_DIR),
        "save_camera_pose_summary_json": True,
        "save_pose2d_csv": False,
        "save_pose2d_vis_video": False,
        "save_pose3d_abs_csv": False,
        "save_pose3d_relative_csv": False,
        "save_pose3d_abs_filtered_csv": False,
        "save_pose3d_relative_filtered_csv": False,
        "save_pose3d_animation": False,
        "animation_source": "relative",
    },

    "paraview_export": {
        "enabled": False,
        "use_filtered_if_available": True,
        "frame_prefix": "paraview_frame_",
        "include_trajectory_history": True,
        "export_segment_endpoints": True,
        "axis_length_m": None,
        "grid_step_m": 0.25,
        "range_margin_m": 0.5,
    },

    "pipeline": {
        "run_sync_check": True,
        "run_build_projection": True,
        "run_pose2d": True,
        "run_pose3d": True,
        "run_pose3d_animation": False,
    },
}
