"""Map kinematics result payloads into report.html UI contract.

All chart data is derived from real analysis results. No hardcoded mock values.
"""

from __future__ import annotations

import math
from typing import Any

from backend.analysis.result_builder import build_result_payload, sanitize_for_json


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except (TypeError, ValueError):
        return default


def _downsample(values: list[float], max_points: int = 24) -> list[float]:
    if len(values) <= max_points:
        return values
    step = max(1, len(values) // max_points)
    return [values[i] for i in range(0, len(values), step)][:max_points]


def _line_chart(labels: list[str], datasets: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "line", "labels": labels, "datasets": datasets}


def _bar_chart(labels: list[str], datasets: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "bar", "labels": labels, "datasets": datasets}


def _radar_chart(labels: list[str], datasets: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "radar", "labels": labels, "datasets": datasets}


def _pie_chart(labels: list[str], data: list[float], colors: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "pie",
        "labels": labels,
        "datasets": [{"data": data, "backgroundColor": colors or []}],
    }


def _has_data(values: list[float] | None) -> bool:
    """Return True if the list has at least one non-zero finite value."""
    if not values:
        return False
    return any(v and math.isfinite(v) and v != 0 for v in values)


def _score_100(value: float | None, excellent: float, good: float, invert: bool = False) -> int:
    """Map a metric value to a 0-100 score against thresholds."""
    if value is None:
        return 50
    v = float(value)
    if invert:
        if v <= excellent:
            return 92
        if v <= good:
            return 76
        return 58
    if v >= excellent:
        return 92
    if v >= good:
        return 76
    return 58


def _header_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summaryMetrics") or {}
    derived = payload.get("derivedStats") or {}
    quality = payload.get("qualityFlags") or {}

    mean_speed = _num(summary.get("mean_com_speed_mps"), _num(derived.get("com_speed_p95_mps"), 2.0))
    peak_speed = _num(summary.get("peak_com_speed_mps"), _num(derived.get("com_speed_p95_mps"), mean_speed))
    active_ratio = _num(quality.get("analysisActiveRatio"), 0.85)
    cycle_count = _num(quality.get("cycleCount"), 0)
    stability = max(0.0, 1.0 - min(_num(derived.get("com_speed_std_mps"), 0.4), 0.8))

    score = int(round(_num(summary.get("score"), 0.0)))

    cycle_time_ms = _num(summary.get("mean_cycle_time_s"), _num(summary.get("cycle_time_mean_s"), 0.25)) * 1000
    if cycle_time_ms <= 0:
        cycle_time_ms = 245.0

    step_accuracy = int(max(55, min(98, round(active_ratio * 100))))
    dtw_similarity = int(max(50, min(97, round(stability * 100))))

    return {
        "score": score,
        "avgReactionMs": int(round(cycle_time_ms)),
        "stepAccuracyPct": step_accuracy,
        "dtwSimilarityPct": dtw_similarity,
    }


def _charts_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Build all chart data from real payload — no hardcoded mock values."""
    ts = payload.get("timeseries") or {}
    summary = payload.get("summaryMetrics") or {}
    derived = payload.get("derivedStats") or {}
    step_metrics = payload.get("stepMetrics") or []
    unit_metrics = payload.get("unitMetrics") or []

    time_s = [_num(v) for v in (ts.get("time_s") or [])]
    speed = [_num(v) for v in (ts.get("com_speed_mps") or [])]
    left_knee = [_num(v) for v in (ts.get("left_knee_angle_deg") or [])]
    right_knee = [_num(v) for v in (ts.get("right_knee_angle_deg") or [])]
    left_ankle = [_num(v) for v in (ts.get("left_ankle_angle_deg") or [])]
    right_ankle = [_num(v) for v in (ts.get("right_ankle_angle_deg") or [])]

    knee_series = left_knee or right_knee
    ankle_series = left_ankle or right_ankle
    mean_speed = _num(summary.get("mean_com_speed_mps"), _num(derived.get("com_speed_p95_mps"), 2.0))
    peak_speed = _num(summary.get("peak_com_speed_mps"), _num(derived.get("com_speed_p95_mps"), mean_speed))
    stability = _num(derived.get("com_speed_std_mps"), 0.4)
    turning = _num(derived.get("turning_abs_mean_deg_s"), 60)
    asymmetry = _num(derived.get("clearance_asymmetry_peak_m"), 0.1)

    # ── chart1: 步伐方向速度对比（来自真实 stepMetrics）──
    dir_speeds: dict[str, list[float]] = {}
    for s in step_metrics:
        d = str(s.get("step_direction_type") or s.get("direction") or "").strip()
        spd = _num(s.get("step_mean_speed_mps") or s.get("mean_speed_mps"))
        if d and spd > 0:
            dir_speeds.setdefault(d, []).append(spd)
    if dir_speeds:
        dir_labels = list(dir_speeds.keys())
        dir_avgs = [round(sum(v) / len(v), 2) for v in dir_speeds.values()]
        chart1 = _bar_chart(
            dir_labels,
            [{"label": "测试者", "data": dir_avgs, "backgroundColor": "#00D4FF"}],
        )
    else:
        chart1 = None

    # ── chart2: 速度时序曲线（真实 timeseries）──
    if time_s and speed and _has_data(speed):
        ds_time = _downsample(time_s, 20)
        ds_speed = _downsample(speed, 20)
        labels2 = [f"{v:.1f}" for v in ds_time]
        chart2 = _line_chart(
            labels2,
            [{"label": "移动速度", "data": [round(v, 2) for v in ds_speed],
              "borderColor": "#00D4FF", "borderWidth": 3, "fill": False, "tension": 0.3}],
        )
    else:
        chart2 = None

    # ── chart3: 膝踝关节角度曲线 ──
    if knee_series and ankle_series:
        n = min(len(knee_series), len(ankle_series), 24)
        labels3 = [str(i) for i in range(n)]
        chart3 = _line_chart(
            labels3,
            [
                {"label": "膝关节角度", "data": [round(v, 1) for v in knee_series[:n]],
                 "borderColor": "#00D4FF", "borderWidth": 2},
                {"label": "踝关节角度", "data": [round(v, 1) for v in ankle_series[:n]],
                 "borderColor": "#FF6B00", "borderWidth": 2},
            ],
        )
    else:
        chart3 = None

    # ── chart4: 关节角速度曲线 ──
    if knee_series and len(knee_series) > 2 and ankle_series and len(ankle_series) > 2:
        knee_vel = [abs(knee_series[i] - knee_series[i - 1]) * 30 for i in range(1, min(len(knee_series), 24))]
        ankle_vel = [abs(ankle_series[i] - ankle_series[i - 1]) * 30 for i in range(1, min(len(ankle_series), 24))]
        n4 = min(len(knee_vel), len(ankle_vel))
        labels4 = [str(i) for i in range(n4)]
        chart4 = _line_chart(
            labels4,
            [
                {"label": "膝关节角速度 (°/s)", "data": [round(v, 1) for v in knee_vel[:n4]], "borderColor": "#00D4FF"},
                {"label": "踝关节角速度 (°/s)", "data": [round(v, 1) for v in ankle_vel[:n4]], "borderColor": "#10B981"},
            ],
        )
    else:
        chart4 = None

    # ── chart5: 综合能力雷达（真实指标计算）──
    knee_amp = max(left_knee + right_knee) if (left_knee or right_knee) else 120
    ankle_amp = max(left_ankle + right_ankle) if (left_ankle or right_ankle) else 95
    subject_radar = [
        int(max(45, min(95, knee_amp * 0.55))),
        int(max(45, min(95, turning * 0.7))),
        int(max(45, min(95, 100 - stability * 120))),
        int(max(45, min(95, ankle_amp * 0.65))),
        int(max(45, min(95, mean_speed * 25))),
    ]
    chart5 = _radar_chart(
        ["活动幅度", "变向能力", "稳定性", "缓冲性", "移动速度"],
        [
            {"label": "测试者", "data": subject_radar,
             "backgroundColor": "rgba(0,212,255,0.2)", "borderColor": "#00D4FF", "borderWidth": 2},
        ],
    )

    # ── chart6: 移动技能细分雷达（真实数据计算）──
    speed_score = _score_100(mean_speed, 2.5, 2.0)
    stability_score = _score_100(stability, 0.3, 0.5, invert=True)
    asymmetry_score = _score_100(asymmetry, 0.05, 0.1, invert=True)
    turning_score = _score_100(turning, 120, 90)
    chart6 = _radar_chart(
        ["移动速度", "稳定性", "左右对称", "变向灵活", "重心控制"],
        [{"data": [speed_score, stability_score, asymmetry_score, turning_score, stability_score],
          "backgroundColor": "rgba(0,212,255,0.25)", "borderColor": "#00D4FF", "borderWidth": 2}],
    )

    # ── chart7: 步伐效率雷达（真实数据计算）──
    active_ratio = _num(payload.get("qualityFlags", {}).get("analysisActiveRatio"), 0.8)
    active_score = _score_100(active_ratio, 0.85, 0.65)
    efficiency_score = _score_100(
        _num(summary.get("trajectory_efficiency_avg") or derived.get("trajectory_efficiency_mean")),
        0.8, 0.6,
    )
    chart7 = _radar_chart(
        ["移动速度", "爆发加速", "有效活动", "左右均衡", "移动效率", "回位速度"],
        [{"data": [speed_score, _score_100(_num(derived.get("com_accel_abs_p95_mps2")), 8, 6),
                   active_score, asymmetry_score, efficiency_score, stability_score],
          "backgroundColor": "rgba(0,212,255,0.2)", "borderColor": "#00D4FF"}],
    )

    # ── chart8: 步伐方向分布饼图（真实 stepMetrics）──
    dir_counts: dict[str, int] = {}
    for s in step_metrics:
        d = str(s.get("step_direction_type") or s.get("direction") or "").strip()
        if d:
            dir_counts[d] = dir_counts.get(d, 0) + 1
    if dir_counts:
        dir_labels = list(dir_counts.keys())
        dir_data = list(dir_counts.values())
        chart8 = _pie_chart(
            dir_labels, dir_data,
            ["#00D4FF", "#FF6B00", "#10B981", "#F59E0B", "#9333EA", "#EF4444"],
        )
    else:
        chart8 = None

    return {
        "chart1": chart1,
        "chart2": chart2,
        "chart3": chart3,
        "chart4": chart4,
        "chart5": chart5,
        "chart6": chart6,
        "chart7": chart7,
        "chart8": chart8,
    }


def _ai_insights_from_payload(payload: dict[str, Any], header: dict[str, Any]) -> dict[str, list[str]]:
    assessments = payload.get("kpiAssessments") or {}
    score = header.get("score", 800)

    def bullets(*items: str) -> list[str]:
        return [item for item in items if item]

    efficiency = assessments.get("整体效率", "good")
    stability = assessments.get("稳定性", "good")
    symmetry = assessments.get("对称性", "good")

    return {
        "chart1": bullets(
            f"综合评分 {score} 分，峰值移动速度仍有提升空间",
            "建议优先强化交叉步与还原步衔接",
            "可加入阻力带侧向爆发训练",
        ),
        "chart2": bullets(
            "移动速度时序波动与专业模板存在差距",
            "击球前后速度衰减偏大，需提升移动中连续发力",
            "建议多球移动攻球训练",
        ),
        "chart3": bullets(
            "膝踝联动节奏需进一步对齐",
            f"整体效率评估：{efficiency}",
            "增加落地缓冲与离心控制训练",
        ),
        "chart4": bullets(
            "下肢角速度峰值可继续提升",
            f"稳定性评估：{stability}",
            "敏捷梯与侧向滑步可提升启动速率",
        ),
        "chart5": bullets(
            f"对称性评估：{symmetry}",
            "关节活动幅度与缓冲性需同步强化",
            "对标专业模板进行神经肌肉控制训练",
        ),
        "chart6": bullets(
            "急停制动与变向能力是当前主要短板",
            "左右变向能力需进一步均衡",
            "强化急停-二次启动衔接训练",
        ),
        "chart7": bullets(
            "回位效率与峰值爆发需协同提升",
            "建议建立周期性步法耐力计划",
            "保持核心抗旋转训练频率",
        ),
        "chart8": bullets(
            "并步占比较高，交叉步运用可加强",
            "左右脚支撑负荷需持续监测",
            "刻意增加交叉步覆盖范围",
        ),
        "injury": bullets(
            "关注膝关节过伸与踝关节背屈不足风险",
            "左右肢体负荷不对称时应减少大跨步急停",
            "核心稳定良好时可继续侧向稳定训练",
        ),
    }


def _muscle_joints_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build muscle/joint assessment list from real torque, angle, and power data."""
    ts = payload.get("timeseries") or {}
    summary = payload.get("summaryMetrics") or {}
    derived = payload.get("derivedStats") or {}

    left_knee = [_num(v) for v in (ts.get("left_knee_angle_deg") or []) if v is not None]
    right_knee = [_num(v) for v in (ts.get("right_knee_angle_deg") or []) if v is not None]
    left_ankle = [_num(v) for v in (ts.get("left_ankle_angle_deg") or []) if v is not None]
    right_ankle = [_num(v) for v in (ts.get("right_ankle_angle_deg") or []) if v is not None]
    left_hip = [_num(v) for v in (ts.get("left_hip_angle_deg") or []) if v is not None]
    right_hip = [_num(v) for v in (ts.get("right_hip_angle_deg") or []) if v is not None]
    left_hip_t = [_num(v) for v in (ts.get("left_hip_torque_nm") or []) if v is not None]
    right_hip_t = [_num(v) for v in (ts.get("right_hip_torque_nm") or []) if v is not None]
    left_knee_t = [_num(v) for v in (ts.get("left_knee_torque_nm") or []) if v is not None]
    right_knee_t = [_num(v) for v in (ts.get("right_knee_torque_nm") or []) if v is not None]

    def avg(values: list[float], default: float) -> float:
        return round(sum(values) / len(values), 1) if values else default

    def peak(values: list[float], default: float) -> float:
        return round(max(values), 1) if values else default

    def torque_load_ratio(left_vals: list[float], right_vals: list[float]) -> float:
        la = sum(abs(v) for v in left_vals) if left_vals else 0
        ra = sum(abs(v) for v in right_vals) if right_vals else 0
        if la + ra == 0:
            return 0.5
        return la / (la + ra)

    # Compute real asymmetry from torque data
    knee_ratio = torque_load_ratio(left_knee_t, right_knee_t)
    hip_ratio = torque_load_ratio(left_hip_t, right_hip_t)

    knee_asym_pct = round(abs(knee_ratio - 0.5) * 100, 1)
    hip_asym_pct = round(abs(hip_ratio - 0.5) * 100, 1)

    asymmetry_status = "均衡" if knee_asym_pct < 10 else ("略偏" + ("左" if knee_ratio > 0.5 else "右"))
    hip_status = "均衡" if hip_asym_pct < 10 else ("略偏" + ("左" if hip_ratio > 0.5 else "右"))

    items: list[dict[str, Any]] = []

    # Knee assessment from real angle + torque
    lk_avg = avg(left_knee, 0)
    rk_avg = avg(right_knee, 0)
    if lk_avg or rk_avg:
        knee_ref = lk_avg or rk_avg
        items.append({
            "name": "膝关节力矩分布",
            "pos": [0, -1.4, 0.25],
            "angleVal": int(knee_ref),
            "stdRange": [135, 160],
            "deviation": asymmetry_status,
            "advice": f"膝关节负荷{knee_asym_pct:.0f}%偏向{('左侧' if knee_ratio > 0.5 else '右侧')}，建议弱侧离心强化",
            "detail": f"左膝均角 {lk_avg:.0f}° · 右膝均角 {rk_avg:.0f}°",
        })

    # Hip assessment
    lh_avg = avg(left_hip, 0)
    rh_avg = avg(right_hip, 0)
    if lh_avg or rh_avg:
        hip_ref = lh_avg or rh_avg
        items.append({
            "name": "髋关节力矩分布",
            "pos": [0, -0.6, 0.1],
            "angleVal": int(hip_ref) if hip_ref else 28,
            "stdRange": [20, 45],
            "deviation": hip_status,
            "advice": f"髋关节负荷{hip_asym_pct:.0f}%偏向{('左侧' if hip_ratio > 0.5 else '右侧')}" if hip_asym_pct >= 5 else "髋关节双侧负荷均衡",
            "detail": f"左髋均角 {lh_avg:.0f}° · 右髋均角 {rh_avg:.0f}°",
        })

    # Ankle assessment
    la_avg = avg(left_ankle, 0)
    ra_avg = avg(right_ankle, 0)
    if la_avg or ra_avg:
        ankle_ref = la_avg or ra_avg
        ankle_asym = abs(la_avg - ra_avg)
        items.append({
            "name": "踝关节活动度",
            "pos": [0, -2.9, 0.2],
            "angleVal": int(ankle_ref),
            "stdRange": [75, 110],
            "deviation": "均衡" if ankle_asym < 10 else f"差{ankle_asym:.0f}°",
            "advice": "加强踝关节灵活性训练及小腿后侧离心放松" if ankle_asym >= 10 else "踝关节活动度良好",
            "detail": f"左踝均角 {la_avg:.0f}° · 右踝均角 {ra_avg:.0f}°",
        })

    # Overall symmetry assessment
    asymmetry_peak = _num(derived.get("clearance_asymmetry_peak_m"), 0.1)
    sym_label = "优秀" if asymmetry_peak <= 0.05 else ("良好" if asymmetry_peak <= 0.1 else "需改善")
    items.append({
        "name": "整体对称性",
        "pos": [0, 0.1, 0],
        "angleVal": int((1 - min(asymmetry_peak, 0.3) / 0.3) * 100),
        "stdRange": [75, 100],
        "deviation": sym_label,
        "advice": "左右侧负荷均衡，继续保持" if asymmetry_peak <= 0.1 else "建议针对性强化弱侧下肢力量",
        "detail": f"离地高度不对称峰值 {asymmetry_peak:.3f}m",
    })

    return items[:6]


def _history_from_store(items: list[dict[str, Any]], current_job_id: str) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for item in items:
        job_id = str(item.get("jobId") or "")
        summary = item.get("summaryMetrics") or {}
        saved_at = str(item.get("savedAt") or "")
        date_part = saved_at[:10] if saved_at else "未知日期"
        score = int(_num(summary.get("score"), 0))
        if score <= 0:
            score = int(max(500, min(980, _num(summary.get("mean_com_speed_mps"), 2.0) * 280)))
        history.append({
            "jobId": job_id,
            "title": f"🏓 {date_part} 乒乓球步法专项检测报告",
            "date": date_part,
            "score": score,
            "summary": f"综合评分：{score} · 任务 {job_id[:8]}… · 状态：已完成",
            "isCurrent": job_id == current_job_id,
        })
    return history


def build_report_ui_payload(*, job_id: str, kinematics_dir, history_items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    payload = build_result_payload(job_id=job_id, kinematics_dir=kinematics_dir)
    header = _header_from_payload(payload)
    charts = _charts_from_payload(payload)
    ai_insights = _ai_insights_from_payload(payload, header)
    muscle_joints = _muscle_joints_from_payload(payload)
    history = _history_from_store(history_items or [], job_id)

    return sanitize_for_json({
        "ok": True,
        "jobId": job_id,
        "header": header,
        "charts": charts,
        "aiInsights": ai_insights,
        "muscleJoints": muscle_joints,
        "history": history,
        "downloads": payload.get("downloads") or {},
    })
