"""Tests for kinematics service integration contracts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

WEB1 = Path(__file__).resolve().parents[1]
if str(WEB1) not in sys.path:
    sys.path.insert(0, str(WEB1))

from backend.analysis import kinematics_service  # noqa: E402


class KinematicsServiceContractTest(unittest.TestCase):
    def test_unpack_segmentation_result_accepts_legacy_two_value_return(self) -> None:
        frame_df = pd.DataFrame({"frame": [1, 2]})
        cycles = [{"cycle_id": 1}]

        unpacked_frame_df, unpacked_cycles, diagnostics = kinematics_service._unpack_segmentation_result(
            (frame_df, cycles)
        )

        self.assertIs(unpacked_frame_df, frame_df)
        self.assertEqual(cycles, unpacked_cycles)
        self.assertEqual(
            {
                "segmentation_status": "ok",
                "segmentation_source": "legacy_two_value_return",
                "cycle_count": 1,
            },
            diagnostics,
        )


if __name__ == "__main__":
    unittest.main()
