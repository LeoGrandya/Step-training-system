"""Persist completed analysis results into MySQL-backed evaluation reports."""

from __future__ import annotations

from typing import Any

from ..repositories import upsert_evaluation_and_report


def build_report_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Align with site/assets/js/pages/report.js saveReportToUserHistory."""
    summary = dict(payload.get("summaryMetrics") or {})
    derived = dict(payload.get("derivedStats") or {})
    quality = dict(payload.get("qualityFlags") or {})

    mean_speed = float(summary.get("mean_com_speed_mps") or derived.get("com_speed_p95_mps") or 0.0)
    active_ratio = float(quality.get("analysisActiveRatio") or 0.85)
    step_accuracy = int(max(55, min(98, round(active_ratio * 100))))

    return {
        "loops": int(quality.get("cycleCount") or 0),
        "avgSpeed": round(mean_speed, 4),
        "symmetry": step_accuracy,
        "totalTime": round(float(derived.get("duration_s") or 0.0), 4),
        "peakAccel": round(float(derived.get("com_accel_abs_p95_mps2") or 0.0), 4),
        "score": int(summary.get("score") or 0),
    }


def upsert_report_for_job(
    *,
    user_id: str,
    job_id: str,
    mode: str,
    step_name: str | None,
    payload: dict[str, Any],
) -> str | None:
    user_id = str(user_id or "").strip()
    job_id = str(job_id or "").strip()
    if not user_id or not job_id:
        return None

    return upsert_evaluation_and_report(
        subject_id=user_id,
        job_id=job_id,
        mode=str(mode or "eval").strip() or "eval",
        step_name=str(step_name or "视频分析").strip()[:120] or "视频分析",
        summary=build_report_summary(payload),
    )
