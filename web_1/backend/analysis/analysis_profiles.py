"""Analysis profiles controlling speed/quality trade-offs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncProfile:
    video_mode: str
    crf: str
    max_audio_seconds: float


@dataclass(frozen=True)
class Pose3dProfile:
    max_frames: int | None
    temporal_filter_enabled: bool
    temporal_filter_window_size: int
    target_analysis_fps: float | None = 60.0
    frame_stride: int | None = None


@dataclass(frozen=True)
class AnalysisProfile:
    name: str
    sync: SyncProfile
    pose3d: Pose3dProfile


FAST = AnalysisProfile(
    name="快速",
    sync=SyncProfile(video_mode="copy", crf="28", max_audio_seconds=45.0),
    pose3d=Pose3dProfile(
        max_frames=None,
        temporal_filter_enabled=True,
        temporal_filter_window_size=3,
        target_analysis_fps=60.0,
        frame_stride=None,
    ),
)

BALANCED = AnalysisProfile(
    name="均衡",
    sync=SyncProfile(video_mode="reencode", crf="23", max_audio_seconds=90.0),
    pose3d=Pose3dProfile(
        max_frames=None,
        temporal_filter_enabled=True,
        temporal_filter_window_size=5,
        target_analysis_fps=60.0,
        frame_stride=None,
    ),
)

QUALITY = AnalysisProfile(
    name="高质量",
    sync=SyncProfile(video_mode="reencode", crf="20", max_audio_seconds=120.0),
    pose3d=Pose3dProfile(
        max_frames=None,
        temporal_filter_enabled=True,
        temporal_filter_window_size=7,
        target_analysis_fps=None,
        frame_stride=1,
    ),
)

DEFAULT_PROFILE = FAST


# 英文→中文映射（向后兼容旧版输入）
_PROFILE_EN_TO_CN = {"fast": "快速", "balanced": "均衡", "quality": "高质量"}

def normalize_profile_name(raw: str | None) -> str:
    value = str(raw or "").strip()
    # 中文值直接返回
    if value in {"快速", "均衡", "高质量"}:
        return value
    # 英文值映射到中文（向后兼容）
    lower = value.lower()
    return _PROFILE_EN_TO_CN.get(lower, DEFAULT_PROFILE.name)


def get_profile(raw: str | None) -> AnalysisProfile:
    name = normalize_profile_name(raw)
    if name == "快速":
        return FAST
    if name == "高质量":
        return QUALITY
    return BALANCED


def resolve_frame_stride(pose3d: Pose3dProfile, source_fps: float | None) -> int:
    """Compute frame stride; explicit frame_stride wins, else derive from target_analysis_fps."""
    if pose3d.frame_stride is not None:
        return max(1, int(pose3d.frame_stride))
    target = pose3d.target_analysis_fps
    if target is None or target <= 0:
        return 1
    fps = float(source_fps or 60.0)
    if fps <= target:
        return 1
    return max(1, round(fps / float(target)))


def effective_analysis_fps(source_fps: float | None, frame_stride: int) -> float | None:
    if not source_fps or source_fps <= 0:
        return None
    stride = max(1, int(frame_stride))
    return round(float(source_fps) / stride, 3)
