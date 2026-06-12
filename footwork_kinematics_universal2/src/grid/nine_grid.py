# -*- coding: utf-8 -*-
"""
九宫格定位模块。

方法 1（绝对定位）：给定全局坐标 (x, y)，返回所在格子编号 1-9。
方法 2（相对位移向量法）：给定相对于起点的位移 (Δx, Δy)，判定目标格子。
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

import numpy as np
import pandas as pd


# 九宫格编号布局（俯视图，从上到下、从右到左）：
#   7  8  9
#   4  5  6
#   1  2  3
#
# 列: X 从右到左 (col=2→X小, col=0→X大)
# 行: Y 从下到上 (row=0→Y小, row=2→Y大)


def estimate_ground_z(frame_df: pd.DataFrame, fallback: float = 0.0) -> float:
    """用足部关键点 5% 分位数估计地面高度。"""
    foot_cols = []
    for prefix in ["left_heel", "right_heel", "left_ankle", "right_ankle",
                   "left_foot_index", "right_foot_index"]:
        col = f"{prefix}_z"
        if col in frame_df.columns:
            foot_cols.append(col)

    if not foot_cols:
        return float(fallback)

    z_vals = pd.concat([pd.to_numeric(frame_df[c], errors="coerce") for c in foot_cols])
    z_vals = z_vals.dropna()
    if z_vals.empty:
        return float(fallback)
    return float(np.percentile(z_vals.to_numpy(), 5))


def estimate_grid_center_xy(frame_df: pd.DataFrame, n_frames: int = 60) -> Tuple[float, float]:
    """用前 N 帧 COM 坐标均值估计 5 号格中心。"""
    sub = frame_df[["com_x", "com_y"]].dropna().head(n_frames)
    if sub.empty:
        return (0.0, 0.0)
    return (float(sub["com_x"].mean()), float(sub["com_y"].mean()))


def locate_cell_absolute(
    x: float, y: float,
    center_xy: Tuple[float, float],
    cell_size: float = 0.9,
    total_size: float = 2.7,
) -> Optional[int]:
    """
    绝对坐标 → 九宫格编号。

    以 5 号格物理中心为 (cx, cy)，边长 total_size 的正方形区域分为 3×3。
    返回 1-9 的格子编号，超出边界返回 None。
    """
    cx, cy = center_xy
    half = total_size / 2.0
    x_min = cx - half
    y_min = cy - half

    if not (x_min <= x <= x_min + total_size and y_min <= y <= y_min + total_size):
        return None

    col = int((x - x_min) // cell_size)
    row_from_bottom = int((y - y_min) // cell_size)

    if col < 0 or col > 2 or row_from_bottom < 0 or row_from_bottom > 2:
        return None

    # 转换为标准编号（col=2→X最小=左边, row=2→Y最大=上边）
    col_std = 2 - col
    row_std = 2 - row_from_bottom
    return row_std * 3 + col_std + 1


def locate_target_cell_relative(
    x_start: float, y_start: float,
    x_end: float, y_end: float,
    center_xy: Tuple[float, float],
    cell_size: float = 0.9,
    total_size: float = 2.7,
) -> Optional[int]:
    """
    相对位移向量法：以起始帧为临时原点，根据 Δx, Δy 判定目标格子。

    将相对位移转换为绝对终点坐标，再用绝对定位查格。
    """
    return locate_cell_absolute(x_end, y_end, center_xy, cell_size, total_size)


def get_relative_displacement(
    x_start: float, y_start: float,
    x_end: float, y_end: float,
) -> Tuple[float, float]:
    """计算相对位移 (Δx, Δy)。"""
    return (x_end - x_start, y_end - y_start)


# 1 号步伐合法目标格
VALID_CELLS_PACE_1 = {1, 2, 3, 4, 6}
# 2 号步伐合法目标格（全台）
VALID_CELLS_PACE_2 = {1, 2, 3, 4, 6, 7, 8, 9}
# 3 号步伐合法目标格
VALID_CELLS_PACE_3 = {7, 8, 9}
# 8 号步伐合法目标格
VALID_CELLS_PACE_8 = {4, 5, 6}

# 九宫格中心坐标（用于最近邻修正的距离计算）
_CELL_CENTERS_RELATIVE = {
    1: (-1, -1), 2: (0, -1), 3: (1, -1),
    4: (-1, 0),  5: (0, 0),  6: (1, 0),
    7: (-1, 1),  8: (0, 1),  9: (1, 1),
}


def correct_target_cell(
    detected_cell: int,
    pace_id: int,
) -> Optional[int]:
    """
    根据步伐类型的亮灯先验约束，修正检测到的目标格。

    - 1 号步伐：若检测到 7/8/9 → 修正到 {1,2,3,4,6} 中最近格
    - 3 号步伐：若检测到 1/2/3/4/6 → 修正到 {7,8,9} 中最近格
    - 其他步伐：不做修正
    """
    if pace_id == 1:
        if detected_cell not in VALID_CELLS_PACE_1:
            return _nearest_cell(detected_cell, VALID_CELLS_PACE_1)
    elif pace_id == 3:
        if detected_cell not in VALID_CELLS_PACE_3:
            return _nearest_cell(detected_cell, VALID_CELLS_PACE_3)
    return detected_cell


def _nearest_cell(cell: int, valid_set: set) -> int:
    """找合法格子中欧氏距离最近的。"""
    if cell not in _CELL_CENTERS_RELATIVE:
        return min(valid_set)
    cx, cy = _CELL_CENTERS_RELATIVE[cell]
    best = None
    best_dist = float("inf")
    for v in valid_set:
        vx, vy = _CELL_CENTERS_RELATIVE[v]
        dist = math.sqrt((cx - vx) ** 2 + (cy - vy) ** 2)
        if dist < best_dist:
            best_dist = dist
            best = v
    return best if best is not None else min(valid_set)
