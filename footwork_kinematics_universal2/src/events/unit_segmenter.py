"""运行时必需。单位步伐切分模块（实现版）

目标：
1. 用 com_cell 的稳定片段切出 5 -> 目标格 -> 5 的单位步伐
2. 输出逐帧：
   - phase_label
   - unit_id
   - target_cell

思路：
- 先把 com_cell 压缩成“稳定片段”（连续同格且长度达到阈值）
- 再寻找模式：稳定5 -> 稳定目标格(非5) -> 稳定5
- 对应一整次“出去 + 回来”记为一个 unit

phase_label 取值：
- idle_5
- move
- target_hold
- restore
- other
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd


# ============================================================
# 【阈值可改】稳定格判定所需最少连续帧数
# ------------------------------------------------------------
# 某个格子连续出现至少这么多帧，才认定为“稳定到达/稳定停留”
# 这个值越大，越稳；但也会让 move / restore 判定更晚
# ============================================================
STABLE_CELL_MIN_FRAMES = 3


@dataclass
class StableSegment:
    cell: int
    start_idx: int
    end_idx: int
    start_frame: int
    end_frame: int


@dataclass
class UnitSegment:
    unit_id: int
    target_cell: int
    move_start_idx: int
    move_end_idx: int
    target_start_idx: int
    target_end_idx: int
    restore_start_idx: int
    restore_end_idx: int
    move_start_frame: int
    move_end_frame: int
    target_start_frame: int
    target_end_frame: int
    restore_start_frame: int
    restore_end_frame: int


def _to_int_cell(v) -> Optional[int]:
    if pd.isna(v):
        return None
    try:
        return int(v)
    except Exception:
        return None


def _extract_stable_segments(frame_metrics: pd.DataFrame) -> List[StableSegment]:
    if "com_cell" not in frame_metrics.columns or frame_metrics.empty:
        return []

    cells = [_to_int_cell(v) for v in frame_metrics["com_cell"].tolist()]
    frame_ids = frame_metrics["frame_id"].astype(int).tolist()

    raw_segments = []
    start = 0
    current = cells[0]

    for i in range(1, len(cells)):
        if cells[i] != current:
            raw_segments.append((current, start, i - 1))
            start = i
            current = cells[i]
    raw_segments.append((current, start, len(cells) - 1))

    stable_segments: List[StableSegment] = []
    for cell, s, e in raw_segments:
        if cell is None:
            continue
        if (e - s + 1) < STABLE_CELL_MIN_FRAMES:
            continue
        stable_segments.append(
            StableSegment(
                cell=cell,
                start_idx=s,
                end_idx=e,
                start_frame=frame_ids[s],
                end_frame=frame_ids[e],
            )
        )
    return stable_segments


def _build_units_from_segments(segments: List[StableSegment], total_len: int, frame_ids: List[int]) -> List[UnitSegment]:
    units: List[UnitSegment] = []
    unit_id = 1

    for i in range(len(segments) - 2):
        home_seg = segments[i]
        target_seg = segments[i + 1]
        return_seg = segments[i + 2]

        if home_seg.cell != 5:
            continue
        if target_seg.cell in (None, 5):
            continue
        if return_seg.cell != 5:
            continue

        move_start_idx = min(home_seg.end_idx + 1, total_len - 1)
        move_end_idx = target_seg.start_idx
        restore_start_idx = min(target_seg.end_idx + 1, total_len - 1)
        restore_end_idx = return_seg.start_idx

        if move_start_idx > move_end_idx:
            continue
        if restore_start_idx > restore_end_idx:
            continue

        units.append(
            UnitSegment(
                unit_id=unit_id,
                target_cell=target_seg.cell,
                move_start_idx=move_start_idx,
                move_end_idx=move_end_idx,
                target_start_idx=target_seg.start_idx,
                target_end_idx=target_seg.end_idx,
                restore_start_idx=restore_start_idx,
                restore_end_idx=restore_end_idx,
                move_start_frame=frame_ids[move_start_idx],
                move_end_frame=frame_ids[move_end_idx],
                target_start_frame=frame_ids[target_seg.start_idx],
                target_end_frame=frame_ids[target_seg.end_idx],
                restore_start_frame=frame_ids[restore_start_idx],
                restore_end_frame=frame_ids[restore_end_idx],
            )
        )
        unit_id += 1

    return units


def segment_units(frame_metrics: pd.DataFrame, settings: Optional[dict] = None) -> pd.DataFrame:
    out = frame_metrics.copy().reset_index(drop=True)

    if "phase_label" not in out.columns:
        out["phase_label"] = pd.NA
    if "unit_id" not in out.columns:
        out["unit_id"] = pd.NA
    if "target_cell" not in out.columns:
        out["target_cell"] = pd.NA

    if "com_cell" not in out.columns or out.empty:
        return out

    out["phase_label"] = "other"
    out.loc[out["com_cell"] == 5, "phase_label"] = "idle_5"

    stable_segments = _extract_stable_segments(out)
    if not stable_segments:
        return out

    frame_ids = out["frame_id"].astype(int).tolist()
    units = _build_units_from_segments(stable_segments, len(out), frame_ids)

    for unit in units:
        out.loc[unit.move_start_idx:unit.move_end_idx, "phase_label"] = "move"
        out.loc[unit.target_start_idx:unit.target_end_idx, "phase_label"] = "target_hold"
        out.loc[unit.restore_start_idx:unit.restore_end_idx, "phase_label"] = "restore"

        out.loc[unit.move_start_idx:unit.restore_end_idx, "unit_id"] = unit.unit_id
        out.loc[unit.move_start_idx:unit.restore_end_idx, "target_cell"] = unit.target_cell

    return out
