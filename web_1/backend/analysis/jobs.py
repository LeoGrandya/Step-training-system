"""In-memory job registry + per-job directory layout."""

from __future__ import annotations

import json
import secrets
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


_UNSET = object()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_job_id() -> str:
    return f"job_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(3)}"


@dataclass
class JobRecord:
    job_id: str
    status: str = "queued"  # queued | running | done | failed
    stage: Optional[str] = None  # sync | pose3d | kinematics
    progress: float = 0.0
    message: str = ""
    error: Optional[str] = None
    error_code: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    fps: float = 60.0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def touch(self) -> None:
        self.updated_at = _now_iso()


def _record_from_meta_dict(d: dict[str, Any]) -> JobRecord:
    return JobRecord(
        job_id=str(d["job_id"]),
        status=str(d.get("status", "queued")),
        stage=d.get("stage"),
        progress=float(d.get("progress", 0.0)),
        message=str(d.get("message", "")),
        error=d.get("error"),
        error_code=d.get("error_code"),
        created_at=str(d.get("created_at", _now_iso())),
        updated_at=str(d.get("updated_at", _now_iso())),
        fps=float(d.get("fps", 60.0)),
        meta=dict(d.get("meta") or {}),
    )


class JobStore:
    """Thread-safe store：内存 + meta.json 磁盘，避免 Flask 重载/重启后 GET 任务 404。"""

    def __init__(self, jobs_root: Path):
        self._jobs_root = Path(jobs_root)
        self._lock = threading.Lock()
        self._jobs: dict[str, JobRecord] = {}
        self._status_writer: Callable[[JobRecord], None] | None = None

    @property
    def jobs_root(self) -> Path:
        return self._jobs_root

    def set_status_writer(self, writer: Callable[[JobRecord], None] | None) -> None:
        self._status_writer = writer

    def _write_status(self, rec: JobRecord) -> None:
        if self._status_writer is None:
            return
        self._status_writer(rec)

    def job_dir(self, job_id: str) -> Path:
        return self._jobs_root / job_id

    def input_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "input"

    def synced_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "synced"

    def pose3d_session_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "pose3d_session"

    def pose3d_out_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "pose3d_out"

    def pose3d_collect_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "pose3d"

    def kinematics_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "kinematics"

    def logs_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "logs"

    def report_dir(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "report"

    def ensure_layout(self, job_id: str) -> Path:
        root = self.job_dir(job_id)
        for sub in (
            self.input_dir(job_id),
            self.synced_dir(job_id),
            self.pose3d_session_dir(job_id),
            self.pose3d_out_dir(job_id),
            self.pose3d_collect_dir(job_id),
            self.kinematics_dir(job_id),
            self.logs_dir(job_id),
            self.report_dir(job_id),
        ):
            sub.mkdir(parents=True, exist_ok=True)
        return root

    def create_job(self, fps: float = 60.0, extra_meta: Optional[dict[str, Any]] = None) -> JobRecord:
        job_id = new_job_id()
        profile = extra_meta if isinstance(extra_meta, dict) else {}
        rec = JobRecord(job_id=job_id, fps=float(fps), meta={"profile": profile})
        with self._lock:
            self._jobs[job_id] = rec
        self._write_status(rec)
        return rec

    def _recover_stale_if_needed(self, rec: JobRecord) -> JobRecord:
        """进程重启后 queued/running 任务无法继续，标记为失败以免前端永远轮询。"""
        if rec.status in ("queued", "running"):
            rec.status = "failed"
            rec.error_code = "INTERRUPTED"
            rec.error = "分析中断：服务已重启或进程结束，请重新点击「开始分析」。"
            rec.message = rec.error
            rec.stage = None
            rec.progress = 0.0
            rec.touch()
            self._write_meta_file_record(rec)
            self._write_status(rec)
        return rec

    def _try_load_from_disk(self, job_id: str) -> Optional[JobRecord]:
        path = self.job_dir(job_id) / "meta.json"
        if not path.is_file():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            rec = _record_from_meta_dict(raw)
            return self._recover_stale_if_needed(rec)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None

    def _write_meta_file_record(self, rec: JobRecord) -> None:
        path = self.job_dir(rec.job_id) / "meta.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec.to_public_dict(), f, ensure_ascii=False, indent=2)

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            cached = self._jobs.get(job_id)
            if cached is not None:
                return cached
        loaded = self._try_load_from_disk(job_id)
        if loaded is None:
            return None
        with self._lock:
            if job_id not in self._jobs:
                self._jobs[job_id] = loaded
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        stage: Any = _UNSET,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        error: Any = _UNSET,
        error_code: Any = _UNSET,
        fps: Optional[float] = None,
        meta_patch: Optional[dict[str, Any]] = None,
    ) -> None:
        if self.get(job_id) is None:
            return
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return
            if status is not None:
                rec.status = status
            if stage is not _UNSET:
                rec.stage = stage
            if progress is not None:
                rec.progress = progress
            if message is not None:
                rec.message = message
            if error is not _UNSET:
                rec.error = error
            if error_code is not _UNSET:
                rec.error_code = error_code
            if fps is not None:
                rec.fps = float(fps)
            if meta_patch:
                rec.meta.update(meta_patch)
            rec.touch()
        self._write_status(rec)

    def write_meta_file(self, job_id: str) -> None:
        rec = self.get(job_id)
        if rec is None:
            return
        self._write_meta_file_record(rec)


def append_log(job_root: Path, line: str) -> None:
    log_dir = job_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "pipeline.log"
    ts = _now_iso()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")
