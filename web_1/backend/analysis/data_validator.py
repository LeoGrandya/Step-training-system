"""Post-analysis data quality validator — checks CSV completeness and writes data_quality.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_CSVS = {
    "frame_metrics.csv": [
        "time_s", "com_x", "com_y", "com_speed_mps",
        "left_clearance_m", "right_clearance_m",
        "left_knee_angle_deg", "right_knee_angle_deg",
    ],
    "session_summary.csv": [],
    "step_metrics.csv": [],
    "unit_metrics.csv": [],
}

OPTIONAL_COLUMNS = [
    "left_hip_torque_nm", "right_hip_torque_nm",
    "left_knee_torque_nm", "right_knee_torque_nm",
    "left_hip_power_w", "right_hip_power_w",
    "left_knee_power_w", "right_knee_power_w",
    "left_hip_angle_deg", "right_hip_angle_deg",
    "left_support_state", "right_support_state",
    "support_mode", "com_cell",
    "com_acceleration_mps2", "turning_speed_deg_s",
    "left_ankle_angle_deg", "right_ankle_angle_deg",
]


def validate_kinematics_output(kinematics_dir: Path) -> dict[str, Any]:
    """Check all expected output files and columns, return quality report."""
    report: dict[str, Any] = {
        "ok": True,
        "severity": "ok",
        "issues": [],
        "files": {},
    }

    for filename, required_cols in REQUIRED_CSVS.items():
        path = kinematics_dir / filename
        file_info: dict[str, Any] = {
            "exists": path.exists(),
            "size_bytes": 0,
            "row_count": 0,
            "columns": [],
            "missing_required_columns": [],
        }

        if path.exists():
            file_info["size_bytes"] = path.stat().st_size
            try:
                df = pd.read_csv(path)
                file_info["row_count"] = int(len(df))
                file_info["columns"] = list(df.columns)

                missing = [c for c in required_cols if c not in df.columns]
                if missing:
                    file_info["missing_required_columns"] = missing
                    report["issues"].append(
                        f"{filename}: 缺少必需列 {missing}"
                    )

                # Optional columns check
                missing_opt = [
                    c for c in OPTIONAL_COLUMNS
                    if c not in df.columns
                ]
                if missing_opt:
                    file_info["missing_optional_columns"] = missing_opt

                # All-NaN column check
                nan_cols = [
                    c for c in df.columns
                    if df[c].isna().all()
                ]
                if nan_cols:
                    file_info["all_nan_columns"] = nan_cols
                    report["issues"].append(
                        f"{filename}: 以下列全为NaN {nan_cols}"
                    )

                # Empty file check
                if len(df) == 0:
                    report["issues"].append(f"{filename}: 文件为空（0行）")
            except Exception as exc:
                file_info["error"] = str(exc)
                report["issues"].append(f"{filename}: 读取失败 - {exc}")
        else:
            report["issues"].append(f"{filename}: 文件不存在")

        report["files"][filename] = file_info

    # Overall verdict
    has_critical = any(
        info.get("missing_required_columns") or not info["exists"]
        for info in report["files"].values()
    )
    report["ok"] = not has_critical
    if not report["issues"]:
        report["severity"] = "ok"
    elif not has_critical:
        report["severity"] = "warning"
    else:
        report["severity"] = "critical"

    return report


def write_quality_report(
    kinematics_dir: Path,
    report_dir: Path | None = None,
) -> Path:
    """Run validation and write data_quality.json. Returns the file path."""
    quality = validate_kinematics_output(kinematics_dir)
    target = (report_dir or kinematics_dir) / "data_quality.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(quality, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target
