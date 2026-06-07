"""Run footwork_kinematics_universal2 pipeline on pose3d CSV."""

from __future__ import annotations

import json
import os
import shutil
import sys
import inspect
from pathlib import Path
from typing import Callable
from copy import deepcopy

import yaml

from .universal2_compat import write_legacy_csv_bundle

def _patch_pandas_fillna_compat() -> None:
    """
    Make pandas-style `.fillna(method=...)` calls work on environments
    where NDFrame.fillna no longer accepts the `method` keyword.
    """
    import pandas as pd  # type: ignore

    original = pd.core.generic.NDFrame.fillna  # type: ignore[attr-defined]
    if getattr(original, "_compat_patched", False):
        return

    def _compat_fillna(self, value=None, method=None, *args, **kwargs):  # type: ignore[no-untyped-def]
        if method is not None:
            m = str(method).lower()
            if m in ("ffill", "pad"):
                return self.ffill()
            if m in ("bfill", "backfill"):
                return self.bfill()
            raise ValueError(f"Unsupported fillna(method={method!r})")
        sig = inspect.signature(original)
        if "value" in sig.parameters:
            return original(self, value=value, *args, **kwargs)
        return original(self, value, *args, **kwargs)

    _compat_fillna._compat_patched = True  # type: ignore[attr-defined]
    pd.core.generic.NDFrame.fillna = _compat_fillna  # type: ignore[attr-defined]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def footwork_root() -> Path:
    return repo_root() / "footwork_kinematics_universal2"


def _ensure_runtime_dependencies() -> None:
    try:
        import openpyxl  # noqa: F401
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "MISSING_DEPENDENCY_OPENPYXL: openpyxl is required for universal2 xlsx exports. "
            "Install with: .venv\\Scripts\\python.exe -m pip install openpyxl>=3.1.5"
        ) from exc


def _segmentation_input_snapshot(frame_df) -> dict:
    import pandas as pd  # type: ignore

    out: dict[str, object] = {"frame_count": int(len(frame_df))}
    for col in ("com_cell", "left_ankle_cell", "right_ankle_cell", "com_speed_mps"):
        if col not in frame_df.columns:
            out[col] = {"exists": False}
            continue
        s = frame_df[col]
        na_count = int(pd.to_numeric(s, errors="coerce").isna().sum()) if len(s) else 0
        out[col] = {
            "exists": True,
            "dtype": str(s.dtype),
            "na_count": na_count,
            "sample": [None if pd.isna(v) else str(v) for v in s.head(5).tolist()],
        }
    return out


def run_kinematics(
    *,
    pose3d_csv: Path,
    output_dir: Path,
    fps: float,
    log_fn: Callable[[str], None],
    profile: dict | None = None,
) -> None:
    _patch_pandas_fillna_compat()
    _ensure_runtime_dependencies()
    root = footwork_root()
    if not pose3d_csv.exists():
        raise FileNotFoundError(f"pose3d CSV 不存在: {pose3d_csv}")

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    base_cfg_path = root / "config" / "settings.yaml"
    with open(base_cfg_path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f) or {}

    runtime_params = {
        "input_csv": str(pose3d_csv.resolve()),
        "fps": float(fps),
        "output_dir": str(output_dir.resolve()),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    cfg_out = output_dir / "settings.runtime.yaml"
    with open(cfg_out, "w", encoding="utf-8") as f:
        yaml.safe_dump(runtime_params, f, allow_unicode=True, sort_keys=False)
    log_fn(f"运动学配置: {cfg_out}")

    # Headless backend before any pyplot import (analysis runs in a worker thread).
    import matplotlib

    matplotlib.use("Agg")

    from src.io.read_pose3d_csv import load_pose3d_long  # type: ignore
    from user_params import USER_PARAMS  # type: ignore
    from src.pipeline.custom_analysis import (  # type: ignore
        build_frame_metrics,
        segment_cycles_by_rules,
        build_state_event_table,
        build_speed_summary_table,
        build_airborne_event_table,
        build_airborne_summary_table,
        build_joint_summary_table,
        build_overall_summary_table,
        build_evaluation_outputs,
        export_all_outputs,
    )

    params = deepcopy(USER_PARAMS)
    params["input_csv"] = str(pose3d_csv.resolve())
    params["fps"] = float(fps)
    params["output_dir"] = str(output_dir.resolve())
    applied_body = dict(params.get("body") or {})

    # Keep existing yaml-based overrides (if present) for grid/ground/plots.
    for key in ("grid", "ground_z", "plots"):
        if key in settings and settings[key] is not None:
            params[key] = settings[key]

    incoming_profile = dict(profile or {})
    body = dict(params.get("body") or {})
    warnings: list[str] = []

    height_cm_raw = incoming_profile.get("height_cm")
    if height_cm_raw is not None:
        try:
            height_cm = float(height_cm_raw)
            if 80.0 <= height_cm <= 250.0:
                body["height_m"] = round(height_cm / 100.0, 4)
            else:
                warnings.append(f"height_cm_out_of_range:{height_cm}")
        except (TypeError, ValueError):
            warnings.append("height_cm_invalid")

    weight_kg_raw = incoming_profile.get("weight_kg")
    if weight_kg_raw is not None:
        try:
            weight_kg = float(weight_kg_raw)
            if 20.0 <= weight_kg <= 300.0:
                body["weight_kg"] = round(weight_kg, 4)
            else:
                warnings.append(f"weight_kg_out_of_range:{weight_kg}")
        except (TypeError, ValueError):
            warnings.append("weight_kg_invalid")

    if body:
        params["body"] = body
    applied_body = dict(params.get("body") or {})

    log_fn(f"读取 Pose3D: {pose3d_csv}")
    pose_df = load_pose3d_long(pose3d_csv, fps=float(params.get("fps", fps)))

    log_fn("逐帧运动学指标…")
    frame_df = build_frame_metrics(pose_df, params)
    log_fn("分段输入摘要: " + json.dumps(_segmentation_input_snapshot(frame_df), ensure_ascii=False))
    try:
        frame_df, cycles, segmentation_diagnostics = segment_cycles_by_rules(frame_df, params)
    except Exception:
        log_fn("分段失败输入摘要: " + json.dumps(_segmentation_input_snapshot(frame_df), ensure_ascii=False))
        raise
    state_event_df = build_state_event_table(cycles, fps=float(params.get("fps", 60.0)))
    speed_summary_df = build_speed_summary_table(frame_df, cycles, fps=float(params.get("fps", 60.0)))
    airborne_events_df = build_airborne_event_table(frame_df, params)
    airborne_summary_df = build_airborne_summary_table(airborne_events_df)
    joint_summary_df = build_joint_summary_table(frame_df, cycles, fps=float(params.get("fps", 60.0)))
    overall_summary_df = build_overall_summary_table(frame_df, speed_summary_df)
    evaluation_summary_df, torque_summary_df, symmetry_detail_df = build_evaluation_outputs(
        frame_df=frame_df,
        speed_summary_df=speed_summary_df,
        overall_summary_df=overall_summary_df,
        params=params,
    )

    export_all_outputs(
        output_dir=output_dir,
        frame_df=frame_df,
        state_event_df=state_event_df,
        speed_summary_df=speed_summary_df,
        airborne_events_df=airborne_events_df,
        airborne_summary_df=airborne_summary_df,
        joint_summary_df=joint_summary_df,
        overall_summary_df=overall_summary_df,
        evaluation_summary_df=evaluation_summary_df,
        torque_summary_df=torque_summary_df,
        symmetry_detail_df=symmetry_detail_df,
        params=params,
    )
    keep_plot_json = os.environ.get("KINEMATICS_EXPORT_PLOT_JSON", "").strip().lower() in ("1", "true", "yes")
    if not keep_plot_json:
        for rel in (
            ("评价参数", "图片数据JSON"),
            ("关节参数", "图片数据JSON"),
            ("腾空参数", "图片数据JSON"),
            ("速度参数", "图片数据JSON"),
        ):
            target = output_dir.joinpath(*rel)
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
                log_fn(f"已清理图表JSON目录: {target}")
    runtime_profile = {
        "profile_input": incoming_profile,
        "body_applied": applied_body,
        "warnings": warnings,
    }
    dump_runtime_profile = (
        os.environ.get("KINEMATICS_DUMP_RUNTIME_PROFILE", "").strip().lower() in ("1", "true", "yes")
    )
    if dump_runtime_profile or incoming_profile or warnings:
        (output_dir / "runtime_profile.json").write_text(
            json.dumps(runtime_profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    segmentation_diagnostics["body_applied"] = applied_body
    if warnings:
        segmentation_diagnostics["profile_warnings"] = warnings
        log_fn("用户体型参数告警: " + ",".join(warnings))
    (output_dir / "segmentation_diagnostics.json").write_text(
        json.dumps(segmentation_diagnostics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log_fn(
        "分段诊断: "
        + json.dumps(
            {
                "segmentation_status": segmentation_diagnostics.get("segmentation_status"),
                "segmentation_source": segmentation_diagnostics.get("segmentation_source"),
                "cycle_count": segmentation_diagnostics.get("cycle_count"),
            },
            ensure_ascii=False,
        )
    )

    write_legacy_csv_bundle(
        output_dir=output_dir,
        frame_df=frame_df,
        state_event_df=state_event_df,
        speed_summary_df=speed_summary_df,
        overall_summary_df=overall_summary_df,
        evaluation_summary_df=evaluation_summary_df,
        torque_summary_df=torque_summary_df,
        segmentation_diagnostics=segmentation_diagnostics,
    )

    # Web pipeline does not use local figure files.
    # Keep it opt-in to avoid matplotlib overhead and noisy warnings.
    if os.environ.get("KINEMATICS_ENABLE_FIGURES", "").strip().lower() in ("1", "true", "yes"):
        # universal2 export_all_outputs already writes figures when plots.enabled is True.
        pass
    log_fn(f"运动学完成: {output_dir}")
