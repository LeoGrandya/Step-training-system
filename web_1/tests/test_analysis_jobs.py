"""Tests for analysis job store runtime behavior."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

WEB1 = Path(__file__).resolve().parents[1]
if str(WEB1) not in sys.path:
    sys.path.insert(0, str(WEB1))

from backend.analysis.jobs import JobRecord, JobStore  # noqa: E402


class AnalysisJobStoreTest(unittest.TestCase):
    def test_update_can_clear_nullable_status_fields_without_losing_omitted_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JobStore(Path(tmp))
            rec = store.create_job()

            store.update(
                rec.job_id,
                stage="kinematics",
                error="previous error",
                error_code="PREVIOUS_ERROR",
            )
            store.update(rec.job_id, progress=0.5)
            current = store.get(rec.job_id)
            self.assertIsNotNone(current)
            self.assertEqual(current.stage, "kinematics")
            self.assertEqual(current.error, "previous error")
            self.assertEqual(current.error_code, "PREVIOUS_ERROR")

            store.update(rec.job_id, stage=None, error=None, error_code=None)
            cleared = store.get(rec.job_id)
            self.assertIsNotNone(cleared)
            self.assertIsNone(cleared.stage)
            self.assertIsNone(cleared.error)
            self.assertIsNone(cleared.error_code)

    def test_recovering_stale_job_writes_failed_status_to_status_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job_id = "job_stale"
            job_dir = root / job_id
            job_dir.mkdir(parents=True)
            rec = JobRecord(
                job_id=job_id,
                status="running",
                stage="kinematics",
                progress=0.7,
            )
            (job_dir / "meta.json").write_text(
                json.dumps(rec.to_public_dict(), ensure_ascii=False),
                encoding="utf-8",
            )

            writes: list[dict[str, object]] = []
            store = JobStore(root)
            store.set_status_writer(lambda record: writes.append(record.to_public_dict()))

            recovered = store.get(job_id)

            self.assertIsNotNone(recovered)
            self.assertEqual(recovered.status, "failed")
            self.assertEqual(recovered.error_code, "INTERRUPTED")
            self.assertIsNone(recovered.stage)
            self.assertEqual(recovered.progress, 0.0)
            self.assertEqual(len(writes), 1)
            self.assertEqual(writes[0]["job_id"], job_id)
            self.assertEqual(writes[0]["status"], "failed")
            self.assertEqual(writes[0]["error_code"], "INTERRUPTED")


if __name__ == "__main__":
    unittest.main()
