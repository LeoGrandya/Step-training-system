"""Call video_sync.run_sync for a job."""

from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    # web_1/backend/analysis/sync_service.py -> parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def run_job_sync(
    *,
    left_in: Path,
    right_in: Path,
    left_out: Path,
    right_out: Path,
    log_fn,
    progress_sink,
    video_mode: str = "reencode",
    crf: str = "20",
    max_audio_seconds: float = 120.0,
) -> dict[str, object]:
    root = _repo_root()
    vs = root / "video_sync"
    if str(vs) not in sys.path:
        sys.path.insert(0, str(vs))
    from lib.sync import require_ffmpeg, run_sync  # type: ignore

    log_fn("检查 FFmpeg…")
    require_ffmpeg()
    mode = str(video_mode or "reencode").strip().lower()
    if mode not in ("copy", "reencode"):
        mode = "reencode"
    log_fn(f"开始双机同步: {left_in.name} + {right_in.name} (mode={mode}, crf={crf}, max_audio_seconds={max_audio_seconds})")
    fallback_used = False
    try:
        run_sync(
            left_in,
            right_in,
            left_out,
            right_out,
            manual_offset=None,
            max_audio_seconds=float(max_audio_seconds),
            crf=str(crf),
            video_mode=mode,
            progress=progress_sink,
        )
    except Exception:
        if mode == "copy":
            fallback_used = True
            mode = "reencode"
            log_fn("copy 模式同步失败，自动回退到 reencode 重试一次。")
            run_sync(
                left_in,
                right_in,
                left_out,
                right_out,
                manual_offset=None,
                max_audio_seconds=float(max_audio_seconds),
                crf=str(crf),
                video_mode=mode,
                progress=progress_sink,
            )
        else:
            raise
    log_fn(f"同步完成: {left_out.name}, {right_out.name}")
    return {"video_mode": mode, "fallback_used": fallback_used}
