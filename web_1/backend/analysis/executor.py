"""Bounded job executor for analysis pipelines."""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable


def _default_workers() -> int:
    raw = os.environ.get("ANALYSIS_MAX_WORKERS", "1").strip()
    try:
        return max(1, min(int(raw), 8))
    except ValueError:
        return 1


def _default_queue_size() -> int:
    raw = os.environ.get("ANALYSIS_MAX_QUEUE", "8").strip()
    try:
        return max(1, min(int(raw), 128))
    except ValueError:
        return 8


class AnalysisExecutor:
    def __init__(self, max_workers: int | None = None):
        workers = max_workers or _default_workers()
        self._pool = ThreadPoolExecutor(max_workers=workers)
        self._capacity = threading.Semaphore(workers + _default_queue_size())
        self._lock = threading.Lock()
        self._running = 0

    def submit(self, fn: Callable[[], None]) -> None:
        if not self._capacity.acquire(blocking=False):
            raise RuntimeError("分析任务排队已满，请稍后重试。")

        def wrapped() -> None:
            with self._lock:
                self._running += 1
            try:
                fn()
            finally:
                with self._lock:
                    self._running = max(0, self._running - 1)
                self._capacity.release()

        self._pool.submit(wrapped)
