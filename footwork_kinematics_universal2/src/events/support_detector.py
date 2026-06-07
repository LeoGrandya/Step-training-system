"""运行时必需。支撑/腾空识别模块（实现版）

输入：
- frame_metrics 中至少需要有：
    - frame_id
    - left_clearance_m
    - right_clearance_m

输出新增列：
- left_support_state: support / airborne
- right_support_state: support / airborne
- support_mode:
    - double_support
    - left_airborne
    - right_airborne
    - double_airborne

说明：
1. 采用“接触阈值 + 腾空阈值”的双阈值滞回逻辑，减少抖动。
2. 支持“连续若干帧才确认切换”的稳定条件。
3. 不修改可视化，只负责逐帧状态计算。
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


# ============================================================
# 【阈值可改】支撑/腾空判定阈值（单位：米）
# ------------------------------------------------------------
# 当离地高度 <= CONTACT_THRESHOLD_M 时，判为“接触地面”
# 当离地高度 >= AIRBORNE_THRESHOLD_M 时，判为“腾空”
# 中间区域保持上一状态，形成滞回，减少抖动误切换
# ============================================================
CONTACT_THRESHOLD_M = 0.020
AIRBORNE_THRESHOLD_M = 0.040

# ============================================================
# 【阈值可改】状态切换稳定帧数
# ------------------------------------------------------------
# 例如设为 2，表示：
# 候选状态连续满足 2 帧，才真正切换 support/airborne
# ============================================================
MIN_CONSECUTIVE_FRAMES = 2


def _candidate_state(clearance_m: Optional[float], prev_state: str) -> str:
    """根据单帧离地高度给出候选状态。"""
    if pd.isna(clearance_m):
        return prev_state
    c = float(clearance_m)
    if c <= CONTACT_THRESHOLD_M:
        return "support"
    if c >= AIRBORNE_THRESHOLD_M:
        return "airborne"
    return prev_state


def _infer_initial_state(series: pd.Series) -> str:
    """根据序列前几帧粗略推断初始状态。默认更保守地认为是支撑。"""
    valid = series.dropna()
    if valid.empty:
        return "support"
    first_val = float(valid.iloc[0])
    if first_val >= AIRBORNE_THRESHOLD_M:
        return "airborne"
    return "support"


def _apply_hysteresis(clearance_series: pd.Series) -> pd.Series:
    """对单只脚应用双阈值 + 连续帧稳定判定。"""
    if clearance_series.empty:
        return pd.Series(dtype="object")

    states = []
    current_state = _infer_initial_state(clearance_series)
    pending_state = current_state
    pending_count = 0

    for clearance in clearance_series.tolist():
        candidate = _candidate_state(clearance, current_state)

        if candidate == current_state:
            pending_state = current_state
            pending_count = 0
        else:
            if candidate == pending_state:
                pending_count += 1
            else:
                pending_state = candidate
                pending_count = 1

            if pending_count >= MIN_CONSECUTIVE_FRAMES:
                current_state = pending_state
                pending_count = 0

        states.append(current_state)

    return pd.Series(states, index=clearance_series.index, dtype="object")


def _compose_support_mode(left_state: str, right_state: str) -> str:
    if left_state == "airborne" and right_state == "airborne":
        return "double_airborne"
    if left_state == "airborne" and right_state == "support":
        return "left_airborne"
    if left_state == "support" and right_state == "airborne":
        return "right_airborne"
    return "double_support"


def detect_support_states(frame_metrics: pd.DataFrame, settings: Optional[dict] = None) -> pd.DataFrame:
    """
    根据左右脚离地高度，输出逐帧支撑/腾空状态。

    参数：
    - frame_metrics: 逐帧参数表，需包含 left_clearance_m / right_clearance_m
    - settings: 预留参数，目前未强制使用；后续如需从 yaml 读阈值可在这里扩展
    """
    out = frame_metrics.copy()

    if "left_clearance_m" not in out.columns or "right_clearance_m" not in out.columns:
        if "left_support_state" not in out.columns:
            out["left_support_state"] = pd.NA
        if "right_support_state" not in out.columns:
            out["right_support_state"] = pd.NA
        if "support_mode" not in out.columns:
            out["support_mode"] = pd.NA
        return out

    left_states = _apply_hysteresis(out["left_clearance_m"])
    right_states = _apply_hysteresis(out["right_clearance_m"])

    out["left_support_state"] = left_states
    out["right_support_state"] = right_states
    out["support_mode"] = [
        _compose_support_mode(l, r)
        for l, r in zip(out["left_support_state"], out["right_support_state"])
    ]
    return out
