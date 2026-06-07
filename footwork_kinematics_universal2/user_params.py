# -*- coding: utf-8 -*-
"""
手动参数入口文件
你只需要改这里，不需要去改其它代码。

重点：
1. input_csv 改成你的 3D 长表 CSV
2. height_m / weight_kg 改成被试身高体重
3. thresholds 里所有阈值都可以手动改
4. 如果九宫格中心点不是自动估计，手动填 center_xy = [x, y]
"""

USER_PARAMS = {
    # ========== 输入 / 输出 ==========
    "input_csv": "session_001/pair_003/pose3d_abs_filtered_zup_ground0.csv",
    "fps": 60.0,
    "output_dir": "./输出结果_按要求版",

    # 若为 None，则自动按足部关键点 5% 分位数估计地面
    "ground_z": None,

    # ========== 人体基础参数（手动输入） ==========
    "body": {
        "height_m": 1.65,
        "weight_kg": 55.0,
    },

    # ========== 九宫格参数 ==========
    "grid": {
        "cell_size_m": 0.9,
        "total_size_m": 2.7,
        # center_estimation_mode: head_mean | static_window | robust_quantile
        "center_estimation_mode": "static_window",
        # 若为 True，会按 COM 轨迹动态扩展总边长（不会缩小）
        "dynamic_total_size_m": True,
        # 例如：[1.35, 1.18]
        # 若为 None，则自动用前 60 帧 COM 平均值估计第 5 格中心
        "center_xy": None,
    },

    # ========== 阈值（全部可手动调整） ==========
    "thresholds": {
        # 进入 n 格
        "entry_com_frames": 3,
        "entry_ankle_frames": 5,

        # 第 n 格停止判定
        "static_com_speed_mps": 0.5,
        "static_ankle_speed_mps": 0.8,
        "static_frames": 3,

        # 第 n 格启动 / 第 5 格启动判定
        "launch_com_speed_mps": 0.3,
        "launch_ankle_speed_mps": 0.5,
        "launch_displacement_m": 0,
        "launch_frames": 3,
        # 同格动作兜底：最小动作信号占比（其余按步事件/移动段覆盖率自适应抬升）
        "inhome_signal_ratio_min": 0.008,
        "inhome_signal_step_ratio_scale": 0.6,
        "inhome_signal_run_ratio_scale": 0.5,

        # 支撑 / 腾空逐帧判定（用于支撑期占比、步数）
        "support_contact_threshold_m": 0.030,
        "support_airborne_threshold_m": 0.040,
        "support_min_frames": 2,

        # 腾空事件
        "single_airborne_height_m": 0.04,
        "single_airborne_min_frames": 5,
        "double_airborne_height_m": 0.030,
        "double_airborne_min_frames": 5,

        # 评价阈值
        "support_ratio_normal_low_pct": 60.0,
        "support_ratio_normal_high_pct": 95.0,
    },

    # ========== 绘图开关 ==========
    "plots": {
        "enabled": True,
    },
}
