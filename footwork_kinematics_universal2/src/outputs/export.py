# -*- coding: utf-8 -*-
"""
输出导出模块 —— 按文件夹组织所有参数。

目录结构：
  输出根目录/
  ├── 00_输出说明.json
  ├── 表1_全局宏观统计表.xlsx
  ├── 表2_多维时序明细表.xlsx
  ├── 逻辑参数/
  ├── 位移参数/
  ├── 速度参数/
  ├── 腾空参数/
  ├── 关节参数/
  └── 评价参数/
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


# ============================================================================
# 表1：全局宏观统计表
# ============================================================================

def build_table1_global_summary(
    frame_df: pd.DataFrame,
    segments: List[Dict],
    airborne_summary: Dict,
    pace_id: int,
    fps: float,
) -> pd.DataFrame:
    """全视频宏观统计。所有耗时从 frame_df phase_label 计算（去重叠）。"""
    has_restore = pace_id in (1, 2, 3)

    # 循环次数（仅 4567）
    cycle_ids = set()
    for s in segments:
        cid = s.get("cycle_id")
        if cid is not None:
            cycle_ids.add(cid)
    cycle_count = len(cycle_ids) if pace_id in (4, 5, 6, 7) else None

    # 移动/还原次数
    move_count = int((frame_df["phase_label"] == "move").sum() > 0)  # 用帧计数校准
    move_count = sum(1 for s in segments if s.get("phase") == "move")
    restore_count = sum(1 for s in segments if s.get("phase") == "restore")

    # 移动步数
    total_steps = int(frame_df["step_event_count"].fillna(0).sum())

    # 运动总耗时
    # 1238: (Total_Frames - Frames_pre_move_stop - Frames_pre_restore_stop) / FPS
    # 4567: (Tend_last_frame - Tstart_1) / FPS
    if has_restore:
        total_motion_frames = int((~frame_df["phase_label"].isin({"pre_move_stop", "pre_restore_stop"})).sum())
    elif pace_id in (4, 5, 6, 7):
        move_ids = frame_df[frame_df["phase_label"] == "move"]["frame_id"]
        if len(move_ids) > 0:
            total_motion_frames = int(move_ids.iloc[-1] - move_ids.iloc[0])
        else:
            total_motion_frames = 0
    else:
        # Type 8: no stop phases
        total_motion_frames = int((~frame_df["phase_label"].isin({"pre_move_stop", "pre_restore_stop"})).sum())
    total_motion_s = total_motion_frames / fps

    # 移动总耗时
    move_mask = frame_df["phase_label"] == "move"
    move_frames = int(move_mask.sum())
    move_total_s = move_frames / fps

    # 还原总耗时
    restore_mask = frame_df["phase_label"] == "restore"
    restore_frames = int(restore_mask.sum())
    restore_total_s = restore_frames / fps

    # 移动总距离
    move_df = frame_df[move_mask]
    total_move_dist = _arc_length(move_df, "com")

    # 还原总距离
    restore_df = frame_df[restore_mask]
    restore_total_dist = _arc_length(restore_df, "com") if has_restore else 0.0

    # 平均速度（123步伐: 运动总距离 = 移动总距离 + 还原总距离）
    if has_restore:
        total_all_dist = total_move_dist + restore_total_dist
        motion_avg = total_all_dist / total_motion_s if total_motion_s > 0 else 0.0
    else:
        motion_avg = total_move_dist / total_motion_s if total_motion_s > 0 else 0.0
    move_avg = total_move_dist / move_total_s if move_total_s > 0 else 0.0
    restore_avg = restore_total_dist / restore_total_s if has_restore and restore_total_s > 0 else 0.0

    row = {
        "循环次数": cycle_count,
        "移动次数": move_count,
        "还原次数": restore_count if has_restore else None,
        "移动步数": total_steps,
        "运动总耗时_s": round(total_motion_s, 4),
        "移动总耗时_s": round(move_total_s, 4),
        "还原总耗时_s": round(restore_total_s, 4) if has_restore else None,
        "移动总距离_m": round(total_move_dist, 4),
        "还原总距离_m": round(restore_total_dist, 4) if has_restore else None,
        "运动总平均速度_mps": round(motion_avg, 4),
        "移动总平均速度_mps": round(move_avg, 4),
        "还原总平均速度_mps": round(restore_avg, 4) if has_restore else None,
    }
    for k, v in airborne_summary.items():
        row[k] = round(v, 4) if v is not None else None
    row = {k: v for k, v in row.items() if v is not None}
    return pd.DataFrame([row])


# ============================================================================
# 表2：多维时序明细表
# ============================================================================

def build_table2_detailed(
    segment_metrics_df: pd.DataFrame,
    evaluation_by_seg: Optional[Dict[str, List[Dict]]] = None,
) -> pd.DataFrame:
    """每段一行的完整参数。合并段级参数 + 评价参数。"""
    df = segment_metrics_df.copy()

    if evaluation_by_seg:
        for key, evals in evaluation_by_seg.items():
            if not isinstance(evals, list):
                df[key] = evals
                continue
            # 构建 segment_id → value 映射
            val_map = {}
            for ev in evals:
                if not isinstance(ev, dict):
                    continue
                sid = ev.get("segment_id")
                if sid is None:
                    continue
                val_map[sid] = _eval_value(ev)
            col = f"评价_{key}"
            df[col] = df["segment_id"].map(val_map)

    return df


def _eval_value(d: Dict) -> Optional[float]:
    """从评价参数字典提取第一个数值（跳过 segment_id, side 等键）。"""
    for k, v in d.items():
        if k in ("segment_id", "side", "phase"):
            continue
        if isinstance(v, (int, float)) and not pd.isna(v):
            return v
    return None


# ============================================================================
# 各文件夹导出
# ============================================================================

def export_all(
    output_dir: Path,
    table1: pd.DataFrame,
    table2: pd.DataFrame,
    frame_df: pd.DataFrame,
    segment_metrics_df: pd.DataFrame,
    evaluation_by_seg: Dict[str, List[Dict]],
    dtw_distance: float,
    params: dict,
    pace_id: int,
):
    """按文件夹组织结构导出所有参数。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    has_restore = pace_id in (1, 2, 3)

    # ---- 根目录 ----
    table1.to_excel(output_dir / "表1_全局宏观统计表.xlsx", index=False)
    table2.to_excel(output_dir / "表2_多维时序明细表.xlsx", index=False)

    fps = float(params.get("fps", 60.0))
    seg_list = segment_metrics_df.to_dict("records")

    # ---- 逻辑参数 ----
    _export_logic(output_dir / "逻辑参数", frame_df, segment_metrics_df,
                  pace_id, fps, has_restore)

    # ---- 位移参数 ----
    _export_displacement(output_dir / "位移参数", frame_df, segment_metrics_df,
                         pace_id, fps, has_restore)

    # ---- 速度参数 ----
    _export_speed(output_dir / "速度参数", frame_df, segment_metrics_df,
                  pace_id, fps, has_restore)

    # ---- 腾空参数 ----
    _export_airborne(output_dir / "腾空参数", frame_df, segment_metrics_df,
                     params, fps, pace_id, has_restore)

    # ---- 关节参数 ----
    _export_joint(output_dir / "关节参数", frame_df, segment_metrics_df,
                  pace_id, fps, has_restore)

    # ---- 评价参数 ----
    _export_evaluation(output_dir / "评价参数", frame_df, segment_metrics_df,
                       evaluation_by_seg, dtw_distance, params, pace_id, fps)

    # ---- 根目录合并汇总 ----
    _export_combined_summary(output_dir, table1, segment_metrics_df,
                             evaluation_by_seg, dtw_distance, params, fps, pace_id)

    # ---- 输出说明 ----
    manifest = _build_manifest(pace_id)
    (output_dir / "00_输出说明.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


# ============================================================================
# 各参数文件夹
# ============================================================================

def _export_logic(out_dir, frame_df, seg_df, pace_id, fps, has_restore):
    out_dir.mkdir(parents=True, exist_ok=True)
    has_restore = pace_id in (1, 2, 3)

    # 段级（直接用 segment_metrics_df 中已有的字段）
    logic_cols = ["时间段", "phase", "帧范围", "耗时_s", "segment_id", "cycle_id"]
    avail = [c for c in logic_cols if c in seg_df.columns]
    sub = seg_df[avail].copy()
    if "reaction_time_s" in frame_df.columns:
        # 反应时间从逐帧表的标注取（每段的 reaction_time_s）
        pass  # TODO
    sub.to_excel(out_dir / "02_段级逻辑参数.xlsx", index=False)

    # 汇总
    move_mask = frame_df["phase_label"] == "move"
    restore_mask = frame_df["phase_label"] == "restore"
    move_count = int(seg_df[seg_df["phase"] == "move"].shape[0]) if "phase" in seg_df.columns else 0
    restore_count = int(seg_df[seg_df["phase"] == "restore"].shape[0]) if "phase" in seg_df.columns else 0

    # 运动总耗时
    if has_restore:
        motion_frames = int((~frame_df["phase_label"].isin({"pre_move_stop", "pre_restore_stop"})).sum())
    elif pace_id in (4, 5, 6, 7):
        move_ids = frame_df[frame_df["phase_label"] == "move"]["frame_id"]
        motion_frames = int(move_ids.iloc[-1] - move_ids.iloc[0]) if len(move_ids) > 0 else 0
    else:
        motion_frames = int((~frame_df["phase_label"].isin({"pre_move_stop", "pre_restore_stop"})).sum())

    # 循环次数 (4567 from segments)
    cycle_count = None
    if pace_id in (4, 5, 6, 7):
        cids = seg_df["cycle_id"].dropna().unique() if "cycle_id" in seg_df.columns else []
        cycle_count = len(cids)

    summary = {
        "循环次数": cycle_count,
        "移动次数": move_count,
        "还原次数": restore_count if has_restore else None,
        "移动步数": int(frame_df["step_event_count"].fillna(0).sum()),
        "移动总耗时_s": round(move_mask.sum() / fps, 4),
        "还原总耗时_s": round(restore_mask.sum() / fps, 4) if has_restore else None,
        "运动总耗时_s": round(motion_frames / fps, 4),
    }
    summary = {k: v for k, v in summary.items() if v is not None}
    pd.DataFrame([summary]).to_excel(out_dir / "03_逻辑参数汇总.xlsx", index=False)


def _export_displacement(out_dir, frame_df, seg_df, pace_id, fps, has_restore):
    out_dir.mkdir(parents=True, exist_ok=True)

    # 逐帧
    cols = ["frame_id", "time_s", "phase_label", "segment_id",
            "com_x", "com_y", "com_z",
            "com_disp_x_m", "com_disp_y_m",
            "com_horizontal_path_m",
            "left_ankle_x", "left_ankle_y", "left_ankle_z",
            "left_ankle_disp_x_m", "left_ankle_disp_y_m",
            "left_ankle_horizontal_path_m",
            "right_ankle_x", "right_ankle_y", "right_ankle_z",
            "right_ankle_disp_x_m", "right_ankle_disp_y_m",
            "right_ankle_horizontal_path_m"]
    avail = [c for c in cols if c in frame_df.columns]
    frame_df[avail].to_csv(out_dir / "01_逐帧位移参数.csv", index=False, encoding="utf-8-sig")

    # 段级
    disp_cols = [c for c in seg_df.columns if "距离" in c or "位移" in c or c in
                 ("时间段", "帧范围", "耗时_s", "phase", "segment_id", "cycle_id")]
    avail_disp = [c for c in disp_cols if c in seg_df.columns]
    seg_df[avail_disp].to_excel(out_dir / "02_段级位移参数.xlsx", index=False)

    # 汇总
    total_dist = _arc_length(frame_df[frame_df["phase_label"] == "move"], "com")
    pd.DataFrame([{"移动总距离_m": round(total_dist, 4)}]).to_excel(
        out_dir / "03_位移参数汇总.xlsx", index=False)


def _export_speed(out_dir, frame_df, seg_df, pace_id, fps, has_restore):
    out_dir.mkdir(parents=True, exist_ok=True)

    # 逐帧
    speed_cols = ["frame_id", "time_s", "phase_label", "segment_id",
                  "com_speed_mps", "com_horizontal_speed_mps", "com_acceleration_mps2",
                  "com_vx_mps", "com_vy_mps", "com_vz_mps",
                  "left_ankle_speed_mps", "left_ankle_horizontal_speed_mps",
                  "left_ankle_acceleration_mps2", "left_ankle_vx_mps", "left_ankle_vy_mps", "left_ankle_vz_mps",
                  "right_ankle_speed_mps", "right_ankle_horizontal_speed_mps",
                  "right_ankle_acceleration_mps2", "right_ankle_vx_mps", "right_ankle_vy_mps", "right_ankle_vz_mps"]
    avail_s = [c for c in speed_cols if c in frame_df.columns]
    frame_df[avail_s].to_csv(out_dir / "01_逐帧速度参数.csv", index=False, encoding="utf-8-sig")

    # 段级（仅速度/加速度，不含角速度）
    spd_keywords = ["合速度", "平均速度", "加速度_mps2", "vx_", "vy_"]
    spd_cols = [c for c in seg_df.columns if any(kw in c for kw in spd_keywords) or c in
                ("时间段", "帧范围", "耗时_s", "phase", "segment_id", "cycle_id")]
    avail_spd = [c for c in spd_cols if c in seg_df.columns]
    seg_df[avail_spd].to_excel(out_dir / "02_段级速度参数.xlsx", index=False)

    # 汇总
    move_mask = frame_df["phase_label"] == "move"
    move_dist = _arc_length(frame_df[move_mask], "com")
    move_time = move_mask.sum() / fps

    # 运动总耗时（与 Table1 一致）
    if has_restore:
        motion_frames = int((~frame_df["phase_label"].isin({"pre_move_stop", "pre_restore_stop"})).sum())
        rst_mask = frame_df["phase_label"] == "restore"
        rst_dist = _arc_length(frame_df[rst_mask], "com")
        total_dist = move_dist + rst_dist
        motion_avg = total_dist / (motion_frames / fps) if motion_frames > 0 else 0
    elif pace_id in (4, 5, 6, 7):
        move_ids = frame_df[frame_df["phase_label"] == "move"]["frame_id"]
        motion_frames = int(move_ids.iloc[-1] - move_ids.iloc[0]) if len(move_ids) > 0 else 0
        total_dist = move_dist
        motion_avg = total_dist / (motion_frames / fps) if motion_frames > 0 else 0
    else:
        motion_frames = int((~frame_df["phase_label"].isin({"pre_move_stop", "pre_restore_stop"})).sum())
        total_dist = move_dist
        motion_avg = total_dist / (motion_frames / fps) if motion_frames > 0 else 0

    summary = {
        "运动总平均速度_mps": round(motion_avg, 4),
        "移动总平均速度_mps": round(move_dist / move_time, 4) if move_time > 0 else 0,
    }
    if has_restore:
        rst_mask = frame_df["phase_label"] == "restore"
        rst_dist = _arc_length(frame_df[rst_mask], "com")
        rst_time = rst_mask.sum() / fps
        summary["还原总平均速度_mps"] = round(rst_dist / rst_time, 4) if rst_time > 0 else 0
        rst_time = rst_mask.sum() / fps
        summary["还原总平均速度_mps"] = round(rst_dist / rst_time, 4) if rst_time > 0 else 0
    pd.DataFrame([summary]).to_excel(out_dir / "03_速度参数汇总.xlsx", index=False)


def _export_airborne(out_dir, frame_df, seg_df, params, fps, pace_id, has_restore):
    out_dir.mkdir(parents=True, exist_ok=True)
    air_cfg = params.get("airborne", {})

    # 逐帧
    air_cols = ["frame_id", "time_s", "phase_label", "segment_id",
                "left_clearance_m", "right_clearance_m",
                "left_support_state", "right_support_state", "support_mode"]
    avail_a = [c for c in air_cols if c in frame_df.columns]
    frame_df[avail_a].to_csv(out_dir / "01_逐帧腾空参数.csv", index=False, encoding="utf-8-sig")

    # 段级
    air_seg_cols = [c for c in seg_df.columns if "airborne" in c or "悬空" in c or c in
                    ("时间段", "帧范围", "耗时_s", "phase", "segment_id", "cycle_id")]
    avail_as = [c for c in air_seg_cols if c in seg_df.columns]
    seg_df[avail_as].to_excel(out_dir / "02_段级腾空参数.xlsx", index=False)

    # 汇总
    summary = _summarize_airborne(frame_df, params, fps)
    pd.DataFrame([summary]).to_excel(out_dir / "03_腾空参数汇总.xlsx", index=False)


def _export_joint(out_dir, frame_df, seg_df, pace_id, fps, has_restore):
    out_dir.mkdir(parents=True, exist_ok=True)

    # 逐帧
    joint_cols = ["frame_id", "time_s", "phase_label", "segment_id",
                  "left_hip_angle_deg", "right_hip_angle_deg",
                  "left_hip_angular_velocity_deg_s", "right_hip_angular_velocity_deg_s",
                  "left_hip_angular_acceleration_deg_s2", "right_hip_angular_acceleration_deg_s2",
                  "left_knee_angle_deg", "right_knee_angle_deg",
                  "left_knee_angular_velocity_deg_s", "right_knee_angular_velocity_deg_s",
                  "left_knee_angular_acceleration_deg_s2", "right_knee_angular_acceleration_deg_s2",
                  "left_ankle_angle_deg", "right_ankle_angle_deg",
                  "left_ankle_angular_velocity_deg_s", "right_ankle_angular_velocity_deg_s",
                  "left_ankle_angular_acceleration_deg_s2", "right_ankle_angular_acceleration_deg_s2",
                  "left_shank_tilt_angle_deg", "right_shank_tilt_angle_deg"]
    avail_j = [c for c in joint_cols if c in frame_df.columns]
    frame_df[avail_j].to_csv(out_dir / "01_逐帧关节参数.csv", index=False, encoding="utf-8-sig")

    # 段级
    jt_cols = [c for c in seg_df.columns if any(kw in c for kw in
               ("ROM", "缓冲", "蹬伸", "制动", "角速度", "角加速度", "倾斜角"))
               or c in ("时间段", "帧范围", "耗时_s", "phase", "segment_id", "cycle_id")]
    avail_jt = [c for c in jt_cols if c in seg_df.columns]
    seg_df[avail_jt].to_excel(out_dir / "02_段级关节参数.xlsx", index=False)

    # 汇总：各关节ROM/缓冲/蹬伸的均值+极值
    jt_summary = {}
    for side in ["左", "右"]:
        for joint in ["髋", "膝", "踝"]:
            for metric in ["ROM_deg", "缓冲极限_deg", "蹬伸极限_deg", "角速度极值_deg_s", "角加速度极值_deg_s2"]:
                col = f"{side}{joint}{metric}"
                if col in seg_df.columns:
                    vals = pd.to_numeric(seg_df[col], errors="coerce").dropna()
                    if not vals.empty:
                        jt_summary[f"{side}{joint}{metric}_均值"] = round(float(vals.mean()), 2)
                        jt_summary[f"{side}{joint}{metric}_最大值"] = round(float(vals.max()), 2)
    # 小腿倾斜角
    for side in ["左", "右"]:
        for m in ["倾斜角极值_deg", "倾斜角均值_deg"]:
            col = f"{side}小腿{m}"
            if col in seg_df.columns:
                vals = pd.to_numeric(seg_df[col], errors="coerce").dropna()
                if not vals.empty:
                    key = f"{side}小腿{m}"
                    jt_summary[f"{key}_均"] = round(float(vals.mean()), 2)
                    jt_summary[f"{key}_最大"] = round(float(vals.max()), 2)
    if jt_summary:
        pd.DataFrame([jt_summary]).to_excel(out_dir / "03_关节参数汇总.xlsx", index=False)


def _export_evaluation(out_dir, frame_df, seg_df, eval_by_seg, dtw, params, pace_id, fps):
    out_dir.mkdir(parents=True, exist_ok=True)

    # 逐帧
    eval_cols = ["frame_id", "time_s", "phase_label", "segment_id",
                 "dso_pct", "envelope_area_m2", "envelope_dar",
                 "trunk_tilt_rate_deg_s"]
    avail_e = [c for c in eval_cols if c in frame_df.columns]
    frame_df[avail_e].to_csv(out_dir / "01_逐帧评价参数.csv", index=False, encoding="utf-8-sig")

    # 段级
    e_rows = []
    for seg in seg_df.to_dict("records"):
        row = {
            "时间段": seg["时间段"],
            "帧范围": seg["帧范围"],
            "耗时_s": seg["耗时_s"],
            "phase": seg.get("phase"),
        }
        for key, evals in (eval_by_seg or {}).items():
            if isinstance(evals, list):
                val_map = {}
                for ev in evals:
                    if isinstance(ev, dict) and "segment_id" in ev:
                        val_map[ev["segment_id"]] = _eval_value(ev)
                row[key] = val_map.get(seg.get("segment_id"))
            else:
                row[key] = evals
        e_rows.append(row)
    pd.DataFrame(e_rows).to_excel(out_dir / "02_段级评价参数.xlsx", index=False)

    # 汇总
    summary = {
        "归一化DTW距离": dtw,
    }
    # 从段级提取全局评价汇总
    if eval_by_seg:
        for key, evals in eval_by_seg.items():
            if isinstance(evals, list):
                vals = [_eval_value(e) for e in evals if isinstance(e, dict)]
                vals = [v for v in vals if v is not None]
                if vals:
                    summary[f"{key}_均值"] = round(float(np.mean(vals)), 4)
                    summary[f"{key}_最大值"] = round(float(np.max(vals)), 4)
                    summary[f"{key}_最小值"] = round(float(np.min(vals)), 4)
    pd.DataFrame([summary]).to_excel(out_dir / "03_评价参数汇总.xlsx", index=False)


# ============================================================================
# 辅助
# ============================================================================

def _arc_length(df: pd.DataFrame, prefix: str) -> float:
    if len(df) < 2:
        return 0.0
    cols = [f"{prefix}_x", f"{prefix}_y", f"{prefix}_z"]
    if not set(cols).issubset(df.columns):
        return 0.0
    dx = df[f"{prefix}_x"].diff().fillna(0.0)
    dy = df[f"{prefix}_y"].diff().fillna(0.0)
    dz = df[f"{prefix}_z"].diff().fillna(0.0)
    return float((dx.pow(2) + dy.pow(2) + dz.pow(2)).pow(0.5).sum())


def _summarize_airborne(frame_df, params, fps) -> Dict:
    from src.metrics.segment_metrics import _extract_runs
    air_cfg = params.get("airborne", {})
    s_min_h = float(air_cfg.get("single_airborne_min_height_m", 0.025))
    s_min_f = int(air_cfg.get("single_airborne_min_frames", 5))
    d_min_h = float(air_cfg.get("double_airborne_min_height_m", 0.020))
    d_min_f = int(air_cfg.get("double_airborne_min_frames", 5))

    result = {}
    for label, mask, min_f, col in [
        ("双脚", (frame_df["left_clearance_m"] >= d_min_h) & (frame_df["right_clearance_m"] >= d_min_h), d_min_f, None),
        ("左脚", frame_df["left_clearance_m"] >= s_min_h, s_min_f, "left_clearance_m"),
        ("右脚", frame_df["right_clearance_m"] >= s_min_h, s_min_f, "right_clearance_m"),
    ]:
        runs = _extract_runs(mask, min_f)
        if runs:
            times, avgs, maxs = [], [], []
            for s, e in runs:
                sub = frame_df.iloc[s:e + 1]
                times.append(len(sub) / fps)
                h = sub[["left_clearance_m", "right_clearance_m"]].mean(axis=1) if label == "双脚" else sub[col]
                avgs.append(float(h.mean()))
                maxs.append(float(h.max()))
            result[f"最大{label}悬空时间_s"] = max(times)
            result[f"最大{label}悬空平均高度_m"] = round(float(np.mean(avgs)), 4)
            result[f"最大{label}悬空高度_m"] = max(maxs)
        else:
            result[f"最大{label}悬空时间_s"] = 0.0
            result[f"最大{label}悬空平均高度_m"] = 0.0
            result[f"最大{label}悬空高度_m"] = 0.0
    return result


def _export_combined_summary(out_dir, table1, seg_df, eval_by_seg, dtw, params, fps, pace_id):
    """根目录汇总：合并所有参数类别的关键指标。"""
    has_restore = pace_id in (1, 2, 3)
    combined = {}

    # 从 Table1 取逻辑参数
    for c in table1.columns:
        combined[c] = table1[c].values[0]

    # 位移汇总
    move_mask = seg_df["phase"].isin(["move", "restore"]) if has_restore else seg_df["phase"] == "move"
    combined["移动总距离_m"] = round(seg_df[move_mask]["重心移动绝对距离_m"].sum(), 4)

    # 速度汇总（段级均值）
    for prefix, name in [("com", "重心"), ("left_ankle", "左脚踝"), ("right_ankle", "右脚踝")]:
        s_col = f"{name}合速度极值_mps"
        a_col = f"{name}平均速度_mps"
        if s_col in seg_df.columns:
            combined[f"{name}合速度峰值_mps"] = round(float(seg_df[s_col].max()), 4)
        if a_col in seg_df.columns:
            combined[f"{name}段均速均值_mps"] = round(float(seg_df[a_col].mean()), 4)

    # DTW
    combined["归一化DTW距离"] = dtw

    # 评价参数汇总
    if eval_by_seg:
        for key, evals in eval_by_seg.items():
            if isinstance(evals, list):
                vals = []
                for e in evals:
                    if isinstance(e, dict):
                        for k, v in e.items():
                            if k not in ("segment_id", "side", "phase") and isinstance(v, (int, float)):
                                vals.append(v)
                vals = [v for v in vals if not pd.isna(v)]
                if vals:
                    combined[f"{key}_均值"] = round(float(np.mean(vals)), 4)

    # 清理 None
    combined = {k: v for k, v in combined.items() if v is not None}
    pd.DataFrame([combined]).to_excel(out_dir / "03_全部参数汇总.xlsx", index=False)


def _build_manifest(pace_id: int) -> Dict:
    return {
        "表1_全局宏观统计表": "全视频宏观统计",
        "表2_多维时序明细表": "每段一行，完整生物力学参数",
        "逻辑参数": ["02_段级逻辑参数.xlsx", "03_逻辑参数汇总.xlsx"],
        "位移参数": ["01_逐帧位移参数.csv", "02_段级位移参数.xlsx", "03_位移参数汇总.xlsx"],
        "速度参数": ["01_逐帧速度参数.csv", "02_段级速度参数.xlsx", "03_速度参数汇总.xlsx"],
        "腾空参数": ["01_逐帧腾空参数.csv", "02_段级腾空参数.xlsx", "03_腾空参数汇总.xlsx"],
        "关节参数": ["01_逐帧关节参数.csv", "02_段级关节参数.xlsx"],
        "评价参数": ["01_逐帧评价参数.csv", "02_段级评价参数.xlsx", "03_评价参数汇总.xlsx"],
    }
