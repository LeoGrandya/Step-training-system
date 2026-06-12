# -*- coding: utf-8 -*-
"""
乒乓球运动员步法运动学周期划分与多维参数计算 —— 主入口
"""
from __future__ import annotations

import traceback
from pathlib import Path
from typing import Dict, List

from user_params import USER_PARAMS
from src.config_loader import load_config, parse_pace_id, PACE_NAMES
from src.io.data_loader import wide_to_long, build_wide_frame
from src.preprocess.butterworth import filter_frame_coordinates
from src.metrics.frame_metrics import build_frame_metrics
from src.metrics.evaluation import (
    compute_torque_power,
    compute_transition_time,
    compute_kli,
    compute_dso,
    compute_envelope_dar,
    compute_efficiency_bq,
    compute_stride_to_energy,
    compute_trajectory_smoothness,
    compute_normalized_dtw,
    compute_joint_work_ratio,
)
from src.segmentation.segmenter import segment_cycles
from src.metrics.segment_metrics import compute_segment_metrics
from src.outputs.export import (
    build_table1_global_summary,
    build_table2_detailed,
    _summarize_airborne,
    export_all,
)


def process_one_video(
    csv_path: Path,
    person_name: str,
    video_id: str,
    group_name: str,
    project_root: Path,
) -> bool:
    print(f"\n{'='*60}")
    print(f"[处理] {csv_path}")
    print(f"  运动员: {person_name} | 视频编号: {video_id} | 组: {group_name}")

    # ---- 0. 配置 ----
    params = load_config(project_root, person_name, video_id, group_name)
    fps = float(params.get("fps", 60.0))
    pace_id = parse_pace_id(video_id)
    pace_name = PACE_NAMES.get(pace_id, f"未知{pace_id}")
    handedness = params.get("handedness", "right")
    light_interval = params.get("light_interval_ms")

    print(f"  步伐: {pace_name} ({pace_id}) | 手别: {handedness}"
          + (f" | 亮灯间隔: {light_interval}s" if light_interval else ""))

    # ---- 1. 读取 ----
    print("  [1/7] 读取数据……")
    pose_long = wide_to_long(csv_path, fps)
    frame_df = build_wide_frame(pose_long, fps)
    print(f"        帧数: {frame_df['frame_id'].nunique()}, 关节数: {pose_long['joint_name'].nunique()}")

    # ---- 2. 滤波 ----
    print("  [2/7] Butterworth 低通滤波……")
    bw = params.get("butterworth", {})
    frame_df = filter_frame_coordinates(frame_df, fps,
                                        float(bw.get("cutoff_hz", 8)),
                                        int(bw.get("order", 4)))

    # ---- 3. 逐帧指标 ----
    print("  [3/7] 计算逐帧运动学指标……")
    frame_df = build_frame_metrics(frame_df, params)

    if frame_df["left_shoulder_x"].isna().all():
        print("  [注意] 无肩关节数据，髋关节角、躯干波动率将为 NaN")

    frame_df = compute_torque_power(frame_df, params)
    frame_df["dso_pct"] = compute_dso(frame_df)
    env = compute_envelope_dar(frame_df)
    frame_df["envelope_area_m2"] = env["envelope_area_m2"]
    frame_df["envelope_dar"] = env["envelope_dar"]

    # ---- 4. 周期切分（纯运动状态） ----
    print("  [4/7] 周期切分……")
    frame_df, segments = segment_cycles(frame_df, pace_id, handedness, light_interval, params)
    print(f"        切分出 {len(segments)} 个时间段")
    if not segments:
        print("  [警告] 未切分出任何时间段")
        return False

    # ---- 5. 段级参数 ----
    print("  [5/7] 计算段级参数……")
    segment_metrics_df = compute_segment_metrics(frame_df, segments, pace_id, params)

    # ---- 6. 评价参数 ----
    print("  [6/7] 计算评价参数……")
    eval_cfg = params.get("evaluation", {})
    seg_cfg = params.get("segmentation", {})
    body = params.get("body", {})
    w_kg = float(body.get("weight_kg", 55))

    eval_by_seg: Dict[str, List[Dict]] = {}

    eval_by_seg["transition_time_s"] = compute_transition_time(
        frame_df, segments,
        float(seg_cfg.get("transition_vel_threshold_mps", 0.3)), fps)

    eval_by_seg["kli_pct"] = compute_kli(
        frame_df, segments,
        float(eval_cfg.get("knee_locking_angle_thr_deg", 175)))

    eval_by_seg["efficiency_bq_pct"] = compute_efficiency_bq(frame_df, segments, w_kg)

    eval_by_seg["trajectory_smoothness_mJ"] = compute_trajectory_smoothness(
        frame_df, segments, w_kg)

    eval_by_seg["stride_to_energy_ratio_mJ"] = compute_stride_to_energy(
        frame_df, segments)

    eval_by_seg["joint_work_ratio_pct"] = compute_joint_work_ratio(frame_df, segments)

    dtw_val = compute_normalized_dtw(
        frame_df, segments,
        int(eval_cfg.get("dtw_normalized_length", 100)))

    # ---- 7. 导出 ----
    print("  [7/7] 生成输出……")
    airborne_summary = _summarize_airborne(frame_df, params, fps)
    table1 = build_table1_global_summary(frame_df, segments, airborne_summary, pace_id, fps)
    table2 = build_table2_detailed(segment_metrics_df, eval_by_seg)

    output_root = params.get("_output_root", Path("./output"))
    output_dir = output_root / pace_name / person_name / video_id

    export_all(output_dir, table1, table2, frame_df, segment_metrics_df,
               eval_by_seg, dtw_val, params, pace_id)

    print(f"  [完成] → {output_dir}")
    return True


def main():
    project_root = Path(__file__).resolve().parent
    bp = USER_PARAMS.copy()

    input_root = Path(bp.get("input_root", "./input"))
    if not input_root.is_absolute():
        input_root = (project_root / input_root).resolve()
    output_root = Path(bp.get("output_root", "./output"))
    if not output_root.is_absolute():
        output_root = (project_root / output_root).resolve()

    print(f"输入: {input_root}\n输出: {output_root}")

    csv_files = sorted(input_root.rglob("pose3d_wide_processed.csv"))
    print(f"[信息] 找到 {len(csv_files)} 个文件\n")

    processed, skipped, failed = 0, 0, 0

    for csv_path in csv_files:
        rel = csv_path.relative_to(input_root)
        parts = rel.parts
        if len(parts) < 4:
            print(f"[跳过] 路径结构异常: {csv_path}")
            skipped += 1
            continue

        group_name = parts[0]
        person_name = parts[1]
        video_dir = parts[2]

        try:
            parse_pace_id(video_dir)
        except (ValueError, IndexError):
            print(f"[跳过] 无法解析步伐: {video_dir}")
            skipped += 1
            continue

        try:
            if process_one_video(csv_path, person_name, video_dir, group_name, project_root):
                processed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [失败] {csv_path}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"全部完成！成功: {processed}, 跳过: {skipped}, 失败: {failed}, 总计: {len(csv_files)}")


if __name__ == "__main__":
    main()
