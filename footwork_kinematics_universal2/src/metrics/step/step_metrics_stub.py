"""
步级参数列定义（实现版）

本次重点补充：
- 步幅：任一只脚从腾空到落地期间，COM 的位移距离
- 步级方向分量：左右 / 前后 / 斜向
- 同侧跨步长度 stride_length_m（同侧连续两次落地之间的 COM 水平距离）
"""

import pandas as pd


STEP_COLUMNS = [
    "step_id",
    "foot_side",
    "start_frame",
    "end_frame",
    "duration_s",
    "swing_time_s",
    "stance_time_s",
    "step_move_distance_m",
    "step_horizontal_path_m",
    "step_length_m",
    "step_length_3d_m",
    "stride_length_m",
    "step_dx_m",
    "step_dy_m",
    "step_dz_m",
    "step_left_right_distance_m",
    "step_front_back_distance_m",
    "step_diagonal_distance_m",
    "step_direction_type",
    "mean_foot_speed_mps",
    "peak_foot_speed_mps",
    "mean_com_speed_mps",
    "mean_foot_acceleration_mps2",
    "peak_foot_acceleration_mps2",
    "mean_com_acceleration_mps2",
    "peak_com_acceleration_mps2",
    "phase_label",
    "unit_id",
]


def build_step_metrics_stub() -> pd.DataFrame:
    return pd.DataFrame(columns=STEP_COLUMNS)
