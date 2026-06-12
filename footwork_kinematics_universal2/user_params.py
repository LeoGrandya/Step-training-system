# -*- coding: utf-8 -*-
"""
乒乓球步法运动学周期划分与多维参数计算 —— 全局可调参数
========================================================================
所有阈值、路径、开关均在此文件手动配置，不需要修改其他代码。
"""

USER_PARAMS = {
    # ============================
    # 1. 输入 / 输出
    # ============================
    "input_root": "./input",
    "output_root": "./output",
    "subject_info_xlsx": "./input/受试者基本信息.xlsx",
    "light_interval_xlsx": "./input/亮灯时间间隔配置.xlsx",
    "fps": 100.0,

    # ============================
    # 2. 地面高度
    # ============================
    # None = 自动用足部关键点 5% 分位数估计
    "ground_z": None,

    # ============================
    # 3. 九宫格参数
    # ============================
    "grid": {
        "cell_size_m": 0.9,          # 单格边长
        "total_size_m": 2.7,         # 九宫格总边长 (3 × cell_size)
        # 5号格中心 (X, Y)；None = 用前 N 帧 COM 平均值自动估计
        "center_xy": None,
        # 自动估计中心使用的帧数
        "center_estimate_frames": 100,
    },

    # ============================
    # 4. 步伐周期切分阈值
    # ============================
    "segmentation": {
        # ---------- 启动判定 ----------
        "launch_com_speed_mps": 0.3,         # 重心合速度超过此值视为启动
        "launch_min_frames": 3,              # 连续满足启动条件的帧数

        # ---------- 停稳判定 ----------
        "static_com_speed_mps": 0.5,         # 重心合速度低于此值视为停稳
        "static_min_frames": 5,              # 连续满足停稳条件的帧数

        # ---------- 8号步伐 COM 位移曲线极值 ----------
        "disp_peak_min_prominence": 0.02,    # 波峰/波谷最小显著度（米）

        # ---------- 7号步伐 5号点速度极小值 ----------
        "midpoint_speed_threshold_mps": 1.0, # 路过5号格时的速度极小值判定阈值

        # ---------- 变向衔接时间 ----------
        "transition_vel_threshold_mps": 0.3, # 变向低速窗合速度阈值
    },

    # ============================
    # 5. 腾空判定阈值
    # ============================
    "airborne": {
        "contact_threshold_m": 0.020,        # 离地高度 ≤ 此值 = 触地
        "airborne_threshold_m": 0.040,        # 离地高度 ≥ 此值 = 腾空
        "min_consecutive_frames": 2,          # 状态切换需连续帧数（滞回）

        # 腾空事件最小帧数
        "single_airborne_min_frames": 5,
        "double_airborne_min_frames": 5,

        # 腾空事件最小高度
        "single_airborne_min_height_m": 0.025,
        "double_airborne_min_height_m": 0.020,
    },

    # ============================
    # 6. 评价参数阈值
    # ============================
    "evaluation": {
        # 屈膝锁关节指数 (KLI)
        "knee_locking_angle_thr_deg": 175.0,  # 膝关节角 ≥ 此值判定为死锁

        # 变向衔接时间
        "transition_vel_threshold_mps": 0.3,

        # 支撑期占比正常范围
        "support_ratio_normal_low_pct": 60.0,
        "support_ratio_normal_high_pct": 95.0,

        # DTW 归一化长度
        "dtw_normalized_length": 100,
    },

    # ============================
    # 7. Butterworth 低通滤波参数
    # ============================
    "butterworth": {
        "order": 4,
        "cutoff_hz": 8.0,
    },

    # ============================
    # 8. 受试者信息 Excel 列映射
    # ============================
    "subject_excel_columns": {
        "name": 0,          # A列: 姓名
        "age": 1,           # B列: 年龄
        "gender": 2,        # C列: 性别
        "height_cm": 3,     # D列: 身高(cm)
        "weight_kg": 4,     # E列: 体重(kg)
        "handedness": 7,    # H列: 优势手 (右/左/右手)
    },

    # ============================
    # 9. 输出开关
    # ============================
    "output": {
        "export_table1_excel": True,
        "export_table2_excel": True,
        "export_per_frame_csv": True,
        "export_plots": True,
    },
}


