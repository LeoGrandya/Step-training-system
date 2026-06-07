"""Filesystem-backed store for completed analysis results."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


logger = logging.getLogger(__name__)


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AnalysisResultStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.items_dir = self.root / "items"
        self.items_dir.mkdir(parents=True, exist_ok=True)

    def _new_result_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"res_{ts}_{uuid4().hex[:6]}"

    def save_result(
        self,
        *,
        job_id: str,
        payload: dict[str, Any],
        job_meta: dict[str, Any],
        report_path: Path | None = None,
    ) -> str:
        result_id = self._new_result_id()
        item = {
            "resultId": result_id,
            "jobId": job_id,
            "savedAt": _now_iso_utc(),
            "profile": (job_meta or {}).get("profile") or {},
            "summaryMetrics": payload.get("summaryMetrics", {}),
            "derivedStats": payload.get("derivedStats", {}),
            "reportPath": str(report_path) if report_path else None,
        }
        path = self.items_dir / f"{result_id}.json"
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            from ..repositories import save_analysis_result_record

            save_analysis_result_record(
                result_id=result_id,
                job_id=job_id,
                payload=payload,
                job_meta=job_meta,
                report_path=report_path,
            )
        except Exception as exc:
            logger.warning(
                "Failed to write analysis result %s for job %s to MySQL: %s: %s",
                result_id,
                job_id,
                type(exc).__name__,
                exc,
            )
        return result_id

    def get_result(self, result_id: str) -> dict[str, Any] | None:
        try:
            from ..repositories import get_analysis_result_record

            db_item = get_analysis_result_record(result_id)
            if db_item is not None:
                return db_item
        except Exception:
            pass
        path = self.items_dir / f"{result_id}.json"
        if not path.exists():
            return None
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        # Backward compatibility: old entries already include full payload.
        if "payload" in item and isinstance(item.get("payload"), dict):
            return item
        report_path = item.get("reportPath")
        if isinstance(report_path, str) and report_path.strip():
            p = Path(report_path)
            if p.exists():
                try:
                    item["payload"] = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    item["payload"] = None
            else:
                item["payload"] = None
        else:
            item["payload"] = None
        return item

    def list_results(self, *, limit: int = 30) -> list[dict[str, Any]]:
        try:
            from ..repositories import list_analysis_result_records

            db_items = list_analysis_result_records(limit=limit)
            if db_items:
                return db_items
        except Exception:
            pass
        files = sorted(self.items_dir.glob("res_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        out: list[dict[str, Any]] = []
        for p in files[: max(1, int(limit))]:
            try:
                item = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            out.append(
                {
                    "resultId": item.get("resultId"),
                    "jobId": item.get("jobId"),
                    "savedAt": item.get("savedAt"),
                    "profile": item.get("profile") or {},
                    "summaryMetrics": item.get("summaryMetrics") or {},
                    "derivedStats": item.get("derivedStats") or {},
                }
            )
        return out
