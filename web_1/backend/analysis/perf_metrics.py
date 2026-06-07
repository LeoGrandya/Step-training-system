"""Structured performance metrics utilities for analysis jobs."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class StageTimer:
    def __init__(self) -> None:
        self._starts: dict[str, float] = {}
        self._rows: dict[str, dict[str, Any]] = {}

    def start(self, name: str) -> None:
        self._starts[name] = time.perf_counter()
        self._rows[name] = {"start_ts": now_iso()}

    def end(self, name: str, **extra: Any) -> None:
        start = self._starts.get(name)
        row = self._rows.setdefault(name, {})
        if start is not None:
            row["duration_s"] = round(time.perf_counter() - start, 3)
        row["end_ts"] = now_iso()
        if extra:
            row.update(extra)

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return {k: dict(v) for k, v in self._rows.items()}


def load_video_probe(path: Path) -> dict[str, Any]:
    import cv2  # type: ignore

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"ok": False, "path": str(path)}
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()
    duration_s = (frames / fps) if fps > 0 else None
    return {
        "ok": True,
        "path": str(path),
        "fps": fps,
        "frames": frames,
        "width": width,
        "height": height,
        "duration_s": duration_s,
    }


def write_perf_snapshot(report_dir: Path, payload: dict[str, Any]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / "perf_metrics.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
