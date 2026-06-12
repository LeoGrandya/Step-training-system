# -*- coding: utf-8 -*-
"""
运动周期切分模块 —— 纯运动状态驱动，不依赖亮灯。

Type A (1/2/3): COM速度 + 九宫格格位 → 4阶段循环
Type B (8):     COM位移X曲线极值点 → 单阶段
Type C (4/5/6/7): COM位移X波峰/波谷 + 手别路径 → 单阶段

亮灯事件仅在切分后回填，用于计算反应时间。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

from src.grid.nine_grid import (
    correct_target_cell,
    locate_target_cell_relative,
)


# ============================================================================
# 主入口
# ============================================================================

def segment_cycles(
    frame_df: pd.DataFrame,
    pace_id: int,
    handedness: str,
    light_interval_s: Optional[float],
    params: dict,
) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    纯运动状态周期切分。亮灯仅用于后续反应时间计算。

    Returns
    -------
    frame_df : pd.DataFrame (附加 phase_label, segment_id, cycle_id 等列)
    segments : List[Dict]
    """
    if pace_id in (1, 2, 3):
        return _segment_type_a(frame_df, pace_id, light_interval_s, params)
    elif pace_id == 8:
        return _segment_type_b(frame_df, pace_id, params)
    elif pace_id in (4, 5, 6, 7):
        return _segment_type_c(frame_df, pace_id, handedness, params)
    else:
        raise ValueError(f"未知步伐编号: {pace_id}")


# ============================================================================
# Type A: 1/2/3 —— 纯运动状态 4 阶段切分
# ============================================================================

def _segment_type_a(
    df: pd.DataFrame,
    pace_id: int,
    light_interval_s: Optional[float],
    params: dict,
) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    状态机切分：
      pre_move_stop  → move → pre_restore_stop → restore → pre_move_stop → ...

    判定标准（全部可配置）：
      - 启动: COM速度 > launch_speed 连续 launch_frames 帧
      - 停稳: COM速度 < static_speed 连续 static_frames 帧
      - 5号格: com_cell == 5
      - 目标格: com_cell != 5 (再经相对位移向量法 + 步伐约束修正)
    """
    fps = float(params.get("fps", 60.0))
    seg_cfg = params.get("segmentation", {})
    launch_speed = float(seg_cfg.get("launch_com_speed_mps", 0.3))
    launch_frames = int(seg_cfg.get("launch_min_frames", 3))
    static_speed = float(seg_cfg.get("static_com_speed_mps", 0.5))
    static_frames = int(seg_cfg.get("static_min_frames", 5))

    grid_cfg = params.get("grid", {})
    center_xy_val = grid_cfg.get("center_xy")
    if not center_xy_val:
        from src.grid.nine_grid import estimate_grid_center_xy
        center_xy = estimate_grid_center_xy(df, grid_cfg.get("center_estimate_frames", 60))
    else:
        center_xy = (float(center_xy_val[0]), float(center_xy_val[1]))
    cell_size = float(grid_cfg.get("cell_size_m", 0.9))
    total_size = float(grid_cfg.get("total_size_m", 2.7))

    n = len(df)
    speed = df["com_speed_mps"].to_numpy(dtype=float)
    cell = pd.to_numeric(df["com_cell"], errors="coerce").to_numpy(dtype=float)

    def _is_launch(i: int) -> bool:
        if i < 0 or i >= n or np.isnan(speed[i]):
            return False
        return speed[i] > launch_speed

    def _is_static(i: int) -> bool:
        if i < 0 or i >= n or np.isnan(speed[i]):
            return False
        return speed[i] < static_speed

    def _is_home(i: int) -> bool:
        if i < 0 or i >= n or np.isnan(cell[i]):
            return False
        return int(cell[i]) == 5

    def _is_non_home(i: int) -> bool:
        if i < 0 or i >= n or np.isnan(cell[i]):
            return False
        return int(cell[i]) != 5

    def _find_launch(start: int, max_search: int = 120) -> int:
        """向前找启动（连续launch_frames帧速度>阈值）。返回启动段第一帧，找不到返回-1。"""
        count = 0
        end = min(start + max_search, n)
        for i in range(start, end):
            if _is_launch(i):
                count += 1
                if count >= launch_frames:
                    return i - launch_frames + 1
            else:
                count = 0
        return -1

    def _find_static(start: int, max_search: int = 300) -> int:
        """向前找停稳（连续static_frames帧速度<阈值）。返回停稳段第一帧，找不到返回-1。"""
        count = 0
        end = min(start + max_search, n)
        for i in range(start, end):
            if _is_static(i):
                count += 1
                if count >= static_frames:
                    return i - static_frames + 1
            else:
                count = 0
        return -1

    def _find_home_static(start: int, max_search: int = 300) -> int:
        """向前找在5号格停稳。返回符合条件的第一帧，找不到返回-1。"""
        count = 0
        end = min(start + max_search, n)
        for i in range(start, end):
            if _is_home(i) and _is_static(i):
                count += 1
                if count >= static_frames:
                    return i - static_frames + 1
            else:
                count = 0
        return -1

    def _find_non_home_static(start: int, max_search: int = 300) -> int:
        """向前找在非5号格停稳。返回符合条件的第一帧，找不到返回-1。"""
        count = 0
        end = min(start + max_search, n)
        for i in range(start, end):
            if _is_non_home(i) and _is_static(i):
                count += 1
                if count >= static_frames:
                    return i - static_frames + 1
            else:
                count = 0
        return -1

    def _detect_target_cell(move_start: int, move_end: int) -> int:
        """用相对位移向量法判定目标格。"""
        move_start = max(0, min(move_start, n - 1))
        move_end = max(0, min(move_end, n - 1))
        sx = df.iloc[move_start]["com_x"]
        sy = df.iloc[move_start]["com_y"]
        ex = df.iloc[move_end]["com_x"]
        ey = df.iloc[move_end]["com_y"]
        if pd.isna(sx) or pd.isna(ex):
            return 6
        c = locate_target_cell_relative(
            float(sx), float(sy), float(ex), float(ey),
            center_xy, cell_size, total_size,
        )
        if c is None:
            return 6
        c2 = correct_target_cell(c, pace_id)
        return c2 if c2 is not None else c

    # ---- 状态机主循环 ----
    segments: List[Dict] = []
    seg_id = 0
    cycle_id = 0

    # 找初始5号格停稳位置
    cursor = _find_home_static(0)
    if cursor < 0:
        cursor = 0

    while cursor < n - static_frames:
        # ============================================================
        # Phase: pre_move_stop（在5号格等待 → 启动）
        # ============================================================
        launch_move = _find_launch(cursor, max_search=300)
        if launch_move < 0:
            # 剩余帧全部归入 pre_move_stop
            if cursor < n:
                seg_id += 1
                segments.append({
                    "segment_id": seg_id, "cycle_id": cycle_id + 1,
                    "phase": "pre_move_stop",
                    "start_idx": cursor, "end_idx": n - 1,
                    "start_frame": int(df.iloc[cursor]["frame_id"]),
                    "end_frame": int(df.iloc[n - 1]["frame_id"]),
                })
            break

        if launch_move > cursor:
            seg_id += 1
            segments.append({
                "segment_id": seg_id, "cycle_id": cycle_id + 1,
                "phase": "pre_move_stop",
                "start_idx": cursor, "end_idx": launch_move - 1,
                "start_frame": int(df.iloc[cursor]["frame_id"]),
                "end_frame": int(df.iloc[launch_move - 1]["frame_id"]),
            })

        # ============================================================
        # Phase: move → 到目标格停稳（包含制动后的静态帧）
        # ============================================================
        target_stop = _find_non_home_static(launch_move + launch_frames, max_search=300)
        if target_stop < 0:
            for j in range(min(launch_move + 300, n) - 1, launch_move, -1):
                if _is_non_home(j) and _is_static(j):
                    target_stop = j - static_frames + 1
                    break
            if target_stop < 0:
                target_stop = min(launch_move + 120, n - 1)

        move_end = min(target_stop + static_frames - 1, n - 1)
        target_cell = _detect_target_cell(launch_move, move_end)

        seg_id += 1
        segments.append({
            "segment_id": seg_id, "cycle_id": cycle_id + 1,
            "phase": "move",
            "from_cell": 5, "to_cell": target_cell,
            "target_cell": target_cell,
            "start_idx": launch_move, "end_idx": move_end,
            "start_frame": int(df.iloc[launch_move]["frame_id"]),
            "end_frame": int(df.iloc[move_end]["frame_id"]),
        })

        cursor = move_end + 1
        if cursor >= n:
            break

        # ============================================================
        # Phase: pre_restore_stop（在目标格静止等待回程启动）
        # ============================================================
        launch_restore = _find_launch(cursor, max_search=300)
        if launch_restore < 0:
            if cursor < n:
                seg_id += 1
                segments.append({
                    "segment_id": seg_id, "cycle_id": cycle_id + 1,
                    "phase": "pre_restore_stop",
                    "target_cell": target_cell,
                    "start_idx": cursor, "end_idx": n - 1,
                    "start_frame": int(df.iloc[cursor]["frame_id"]),
                    "end_frame": int(df.iloc[n - 1]["frame_id"]),
                })
            break

        if launch_restore > cursor:
            seg_id += 1
            segments.append({
                "segment_id": seg_id, "cycle_id": cycle_id + 1,
                "phase": "pre_restore_stop",
                "target_cell": target_cell,
                "start_idx": cursor, "end_idx": launch_restore - 1,
                "start_frame": int(df.iloc[cursor]["frame_id"]),
                "end_frame": int(df.iloc[launch_restore - 1]["frame_id"]),
            })

        # ============================================================
        # Phase: restore → 回5号格停稳（包含制动后的静态帧）
        # ============================================================
        home_stop = _find_home_static(launch_restore + launch_frames, max_search=300)
        if home_stop < 0:
            for j in range(min(launch_restore + 300, n) - 1, launch_restore, -1):
                if _is_home(j) and _is_static(j):
                    home_stop = j - static_frames + 1
                    break
            if home_stop < 0:
                home_stop = min(launch_restore + 120, n - 1)

        restore_end = min(home_stop + static_frames - 1, n - 1)

        seg_id += 1
        segments.append({
            "segment_id": seg_id, "cycle_id": cycle_id + 1,
            "phase": "restore",
            "from_cell": target_cell, "to_cell": 5,
            "target_cell": target_cell,
            "start_idx": launch_restore, "end_idx": restore_end,
            "start_frame": int(df.iloc[launch_restore]["frame_id"]),
            "end_frame": int(df.iloc[restore_end]["frame_id"]),
        })

        cursor = restore_end + 1
        cycle_id += 1

    # ---- 匹配亮灯事件计算反应时间 ----
    light_events = _build_light_timeline(df, light_interval_s, fps)
    _attach_reaction_times(segments, light_events, fps)

    return _annotate_frame_df(df, segments), segments


def _build_light_timeline(
    df: pd.DataFrame,
    light_interval_s: Optional[float],
    fps: float,
) -> List[Dict]:
    """构建亮灯事件时间线。偶数=目标格亮灯，奇数=5号格亮灯。"""
    if light_interval_s is None or light_interval_s <= 0:
        return []
    interval_frames = int(round(light_interval_s * fps))
    n = len(df)
    events = []
    frame = 2  # 第一盏灯在 frame 2
    idx = 0
    while frame < n:
        is_target = (idx % 2 == 0)
        events.append({
            "light_idx": idx,
            "frame": frame,
            "is_target_light": is_target,
        })
        frame += interval_frames
        idx += 1
    return events


def _attach_reaction_times(
    segments: List[Dict],
    light_events: List[Dict],
    fps: float,
) -> None:
    """将亮灯事件匹配到对应的移动/还原段，计算反应时间。

    第k次移动 → 第(2k)盏灯（偶数索引 = 目标格灯）
    第k次还原 → 第(2k+1)盏灯（奇数索引 = 5号格灯）
    """
    if not light_events:
        return

    move_idx = 0
    restore_idx = 0

    for seg in segments:
        phase = seg.get("phase", "")
        if phase == "move":
            light_pos = move_idx * 2  # 偶数亮灯事件
            if light_pos < len(light_events):
                tlight_frame = light_events[light_pos]["frame"]
                tstart_frame = seg["start_frame"]
                reaction_s = max(0, tstart_frame - tlight_frame) / fps
                seg["light_frame"] = tlight_frame
                seg["reaction_time_s"] = round(reaction_s, 4)
            move_idx += 1
        elif phase == "restore":
            light_pos = restore_idx * 2 + 1  # 奇数亮灯事件
            if light_pos < len(light_events):
                tlight_frame = light_events[light_pos]["frame"]
                tstart_frame = seg["start_frame"]
                reaction_s = max(0, tstart_frame - tlight_frame) / fps
                seg["light_frame"] = tlight_frame
                seg["reaction_time_s"] = round(reaction_s, 4)
            restore_idx += 1

    # 第一个 move 也记录反应时间（4567 步伐用）
    # 不做特殊处理，由调用方决定是否使用


# ============================================================================
# Type B: 8 —— COM位移极值点切分
# ============================================================================

def _segment_type_b(
    df: pd.DataFrame,
    pace_id: int,
    params: dict,
) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    8号步伐：用 com_disp_x_m 曲线的波峰/波谷/平原点切分连续移动段。
    每个相邻分界点之间为一个移动段。无还原无停止。
    """
    seg_cfg = params.get("segmentation", {})
    launch_speed = float(seg_cfg.get("launch_com_speed_mps", 0.3))
    prominence = float(seg_cfg.get("disp_peak_min_prominence", 0.02))

    disp = df["com_disp_x_m"].interpolate(limit_direction="both").to_numpy(dtype=float)
    speed = df["com_speed_mps"].to_numpy(dtype=float)
    n = len(disp)

    # 找波峰、波谷
    peak_idx = argrelextrema(disp, np.greater, order=5)[0]
    valley_idx = argrelextrema(disp, np.less, order=5)[0]

    peak_idx = [p for p in peak_idx if disp[p] > prominence]
    valley_idx = [v for v in valley_idx if disp[v] < -prominence]

    # 找速度接近0的平原区（5号格到位）
    plateau_idx = []
    for i in range(1, n - 1):
        if abs(disp[i]) < 0.05 and speed[i] < 1.0:
            plateau_idx.append(i)

    # 合并排序
    all_points = sorted(set(list(peak_idx) + list(valley_idx) + plateau_idx))
    if len(all_points) < 2:
        return df, []

    # 切分段（无间隙、无重叠）
    segments = []
    seg_id = 0
    for i in range(len(all_points) - 1):
        s = all_points[i]
        e = all_points[i + 1]
        if e - s < 2:
            continue
        seg_end = e - 1  # 不重叠

        prev_to = segments[-1]["to_cell"] if segments else 5

        if disp[e] > disp[s]:
            from_c, to_c = prev_to, 6
        else:
            from_c, to_c = prev_to, 4

        seg_id += 1
        segments.append({
            "segment_id": seg_id, "cycle_id": seg_id,
            "phase": "move",
            "from_cell": from_c, "to_cell": to_c,
            "start_idx": s, "end_idx": seg_end,
            "start_frame": int(df.iloc[s]["frame_id"]),
            "end_frame": int(df.iloc[seg_end]["frame_id"]),
        })

    # 覆盖头尾
    if segments and all_points:
        if all_points[0] > 0:
            segments[0]["start_idx"] = 0
            segments[0]["start_frame"] = int(df.iloc[0]["frame_id"])
        last_covered = segments[-1]["end_idx"]
        if last_covered < n - 1:
            segments[-1]["end_idx"] = n - 1
            segments[-1]["end_frame"] = int(df.iloc[n - 1]["frame_id"])

    return _annotate_frame_df(df, segments), segments


# ============================================================================
# Type C: 4/5/6/7 —— COM位移波峰/波谷 + 路径模板
# ============================================================================

# 各步伐的亮灯路径（不包含起点5）
ROUTE_TEMPLATES = {
    4: [4, 6],        # 两点: 5→4→6→4→6→...
    5: [6, 5, 4],     # 三点: 5→6→5→4→5→6→...
    6: [4, 5, 6],     # 四点: 5→4→5→6→5→4→...
    7: [4, 6, 5, 4],  # 推侧扑: 5→4→6→5→4
}


def _segment_type_c(
    df: pd.DataFrame,
    pace_id: int,
    handedness: str,
    params: dict,
) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    4/5/6/7 步伐切分：
    - 用 com_disp_x_m 曲线波峰/波谷切分
    - 手别决定方向解释（左手镜像）
    - 7号步伐特殊处理 6→4 中间的5号格路过
    """
    seg_cfg = params.get("segmentation", {})
    prominence = float(seg_cfg.get("disp_peak_min_prominence", 0.02))
    midpoint_spd = float(seg_cfg.get("midpoint_speed_threshold_mps", 1.0))

    route = ROUTE_TEMPLATES.get(pace_id, [])
    # 左手镜像：4↔6
    if handedness == "left":
        route = [_mirror_cell(c) for c in route]

    disp = df["com_disp_x_m"].interpolate(limit_direction="both").to_numpy(dtype=float)
    speed = df["com_speed_mps"].to_numpy(dtype=float)
    n = len(disp)

    # 找所有极值点
    peaks = argrelextrema(disp, np.greater, order=3)[0]
    valleys = argrelextrema(disp, np.less, order=3)[0]
    peaks = [p for p in peaks if disp[p] > prominence]
    valleys = [v for v in valleys if disp[v] < -prominence]

    all_extrema = sorted(set(list(peaks) + list(valleys)))
    if len(all_extrema) < 2:
        return df, []

    segments = []
    seg_id = 0

    for i in range(len(all_extrema) - 1):
        s = all_extrema[i]
        e = all_extrema[i + 1]
        if e - s < 2:
            continue

        # 段边界不重叠: 当前段从 s 到 e-1，下一段从 e 开始
        seg_end = e - 1

        # 方向判定
        if disp[s] <= 0 and disp[e] >= 0:
            from_c, to_c = 4, 6
        elif disp[s] >= 0 and disp[e] <= 0:
            from_c, to_c = 6, 4
        else:
            continue

        if handedness == "left":
            from_c = _mirror_cell(from_c)
            to_c = _mirror_cell(to_c)

        # 7号步伐特殊处理
        if pace_id == 7 and from_c == 6 and to_c == 4 and e - s > 10:
            mid_speeds = speed[s:e + 1]
            mid_local = int(np.argmin(mid_speeds))
            mid_global = s + mid_local
            if speed[mid_global] < midpoint_spd and abs(disp[mid_global]) < 0.1:
                seg_id += 1
                segments.append({
                    "segment_id": seg_id, "cycle_id": 1,
                    "phase": "move",
                    "from_cell": 6 if handedness != "left" else 4,
                    "to_cell": 5,
                    "start_idx": s, "end_idx": mid_global - 1,
                    "start_frame": int(df.iloc[s]["frame_id"]),
                    "end_frame": int(df.iloc[mid_global - 1]["frame_id"]),
                })
                seg_id += 1
                segments.append({
                    "segment_id": seg_id, "cycle_id": 1,
                    "phase": "move",
                    "from_cell": 5,
                    "to_cell": 4 if handedness != "left" else 6,
                    "start_idx": mid_global, "end_idx": seg_end,
                    "start_frame": int(df.iloc[mid_global]["frame_id"]),
                    "end_frame": int(df.iloc[seg_end]["frame_id"]),
                })
                continue

        seg_id += 1
        segments.append({
            "segment_id": seg_id,
            "cycle_id": (seg_id - 1) // len(route) + 1 if route else 1,
            "phase": "move",
            "from_cell": from_c, "to_cell": to_c,
            "start_idx": s, "end_idx": seg_end,
            "start_frame": int(df.iloc[s]["frame_id"]),
            "end_frame": int(df.iloc[seg_end]["frame_id"]),
        })

    # 覆盖尾部: 最后一个极值点到视频结束
    if segments and all_extrema:
        last_covered = segments[-1]["end_idx"]
        if last_covered < n - 1:
            segments[-1]["end_idx"] = n - 1
            segments[-1]["end_frame"] = int(df.iloc[n - 1]["frame_id"])

    # 覆盖头部: 视频开始到第一个极值点
    if segments and all_extrema[0] > 0:
        segments[0]["start_idx"] = 0
        segments[0]["start_frame"] = int(df.iloc[0]["frame_id"])

    return _annotate_frame_df(df, segments), segments


def _mirror_cell(c: int) -> int:
    m = {4: 6, 6: 4}
    return m.get(c, c)


# ============================================================================
# 通用
# ============================================================================

def _annotate_frame_df(
    df: pd.DataFrame,
    segments: List[Dict],
) -> pd.DataFrame:
    """写回逐帧标注。段不重叠（状态机保证）。"""
    out = df.copy()
    out["phase_label"] = "unassigned"
    out["segment_id"] = pd.NA
    out["cycle_id"] = pd.NA
    out["target_cell"] = pd.NA
    out["from_cell"] = pd.NA
    out["to_cell"] = pd.NA

    for seg in segments:
        s = max(0, seg["start_idx"])
        e = min(len(out) - 1, seg["end_idx"])
        if s > e:
            continue
        out.loc[s:e, "phase_label"] = seg["phase"]
        out.loc[s:e, "segment_id"] = seg["segment_id"]
        out.loc[s:e, "cycle_id"] = seg.get("cycle_id", pd.NA)
        out.loc[s:e, "target_cell"] = seg.get("target_cell", pd.NA)
        out.loc[s:e, "from_cell"] = seg.get("from_cell", pd.NA)
        out.loc[s:e, "to_cell"] = seg.get("to_cell", pd.NA)

    return out
