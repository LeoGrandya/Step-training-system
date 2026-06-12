"""Regression tests for report UI and downloadable CSV outputs."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

WEB1 = Path(__file__).resolve().parents[1]
if str(WEB1) not in sys.path:
    sys.path.insert(0, str(WEB1))

from backend.analysis.report_ui_builder import _header_from_payload  # noqa: E402
from backend.analysis.universal2_compat import write_legacy_csv_bundle  # noqa: E402


class ReportOutputRegressionTest(unittest.TestCase):
    def test_report_ui_header_score_uses_persisted_result_score_even_when_zero(self) -> None:
        header = _header_from_payload(
            {
                "summaryMetrics": {
                    "score": 0,
                    "mean_com_speed_mps": 0.1738,
                    "peak_com_speed_mps": 0.6148,
                },
                "derivedStats": {
                    "com_speed_std_mps": 0.1235,
                    "com_speed_p95_mps": 0.4167,
                },
                "qualityFlags": {
                    "analysisActiveRatio": 0,
                    "cycleCount": 0,
                },
            }
        )

        self.assertEqual(0, header["score"])

    def test_zero_cycle_legacy_csv_bundle_writes_schema_headers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_legacy_csv_bundle(
                output_dir=output_dir,
                frame_df=pd.DataFrame(
                    {
                        "frame_id": [0, 1],
                        "time_s": [0.0, 0.02],
                        "com_speed_mps": [0.1, 0.2],
                        "step_event_count": [0, 0],
                    }
                ),
                state_event_df=pd.DataFrame(),
                speed_summary_df=pd.DataFrame(),
                overall_summary_df=pd.DataFrame(),
                evaluation_summary_df=pd.DataFrame(),
                torque_summary_df=pd.DataFrame(),
                segmentation_diagnostics={"cycle_count": 0, "segmentation_status": "ok"},
            )

            step_text = (output_dir / "step_metrics.csv").read_text(encoding="utf-8-sig")
            unit_text = (output_dir / "unit_metrics.csv").read_text(encoding="utf-8-sig")
            step_size = (output_dir / "step_metrics.csv").stat().st_size
            unit_size = (output_dir / "unit_metrics.csv").stat().st_size

        self.assertIn("step_id", step_text.splitlines()[0])
        self.assertIn("unit_id", unit_text.splitlines()[0])
        self.assertGreater(step_size, 5)
        self.assertGreater(unit_size, 5)


if __name__ == "__main__":
    unittest.main()
