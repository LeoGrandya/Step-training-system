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
DATA_ROOT = PROJECT_ROOT / "data"
OUTPUT_ROOT = PROJECT_ROOT / "output"

SETTINGS = {
    "input": {
        "data_root": str(DATA_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "groups": ["D:/video", "D:/adult_video1", "D:/adult_video2"],
        "allowed_extensions": [".mp4", ".avi", ".mov", ".mkv"],
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
        # stereo_params_json 由各组目录下的 stereo_params.json 决定，运行时自动解析
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
            # points_json_path 由运行时根据 pair 输出目录自动设置
            "display_scale": 1.0,
            "click_radius_px": 30,
            "show_help": True,
            "window_name_prefix": "ground_control_manual",
        },
        "debug": {
            "save_debug_images": True,
            # debug_dir 由运行时根据 pair 输出目录自动设置
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

    # 将绝对 3D 坐标整体平移，使脚部平均高度贴近 z=0（不做时间滤波）
    "ground_alignment": {
        "enabled": True,
        "joint_names": [
            "left_heel", "right_heel",
            "left_ankle", "right_ankle",
            "left_foot_index", "right_foot_index",
        ],
        "statistic": "mean",
        "target_z": 0.0,
    },

    "outputs": {
        # output_dir 由运行时根据 pair 输出目录自动设置
        "save_camera_pose_summary_json": True,
        "save_pose2d_csv": False,
        "save_pose2d_vis_video": False,
        "save_pose3d_abs_csv": True,
        "save_pose3d_relative_csv": False,
        "save_pose3d_abs_ground_aligned_csv": False,
        "save_pose3d_wide_csv": True,
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
    },

    # =============================
    # 数据后处理：异常值 → 短缺失插值 → 滤波
    # =============================
    "postprocess": {
        # 采样率（Hz）。应与你视频的实际帧率一致。
        "fps": 100.0,

        # 坐标列识别：默认自动识别所有 _x/_y/_z 结尾的列。
        "coordinate_columns": "auto",

        # 最终输出文件名。
        "final_output_name": "pose3d_wide_processed.csv",

        # 异常值处理：滑动窗口 median + MAD
        "outlier": {
            "enabled": True,

            # 滑动窗口大小（帧），必须是奇数。100fps 下 19 帧约 0.19s。
            "window_size": 19,

            # MAD 阈值 k：2.0-2.5 严格；3.0 常用；3.5-4.0 适合快速步伐。
            "mad_k": 3.5,

            # 是否使用 1.4826 × MAD 近似标准差尺度。
            "use_scaled_mad": True,

            # 防止 MAD 太小导致正常点被过度判为异常。
            "min_mad": 1e-6,

            # 异常值是否替换为 NaN。
            "replace_with_nan": True,

            # 跳过不做异常检测的列。
            "skip_columns": [],
        },

        # 短缺失插值
        "interpolation": {
            "enabled": True,

            # pchip：保形无过冲；makima/akima：曲线更自然但可能有过冲；linear：兜底。
            "method": "pchip",

            # 小于等于 n 帧的连续缺失才补齐。100fps 下 25 帧 = 0.25s。
            "max_gap_frames": 25,

            # 三次插值最少需要几个有效点；不足时自动退化为线性。
            "min_valid_points": 4,

            # 只补中间的缺失，不补开头/结尾。
            "inside_only": True,
        },

        # 低通滤波
        "filter": {
            "enabled": True,

            # butterworth：巴特沃斯零相位低通；savgol：Savitzky-Golay 平滑。
            "method": "butterworth",

            # 巴特沃斯滤波器阶数。
            "butterworth_order": 4,

            # 截止频率（Hz）。6 Hz 适合快速步伐，可调 4-8 Hz。
            "cutoff_hz": 6.0,

            # Savitzky-Golay 窗口大小（帧），必须是奇数。
            "savgol_window": 19,
            "savgol_polyorder": 3,
        },
    },
}
