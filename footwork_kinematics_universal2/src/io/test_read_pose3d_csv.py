"""Tests for Pose3D CSV loading formats."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .read_pose3d_csv import load_pose3d_long


class ReadPose3dCsvTests(unittest.TestCase):
    def test_load_pose3d_long_accepts_processed_wide_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "pose3d_wide_processed.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "frame_id,body_com_x,body_com_y,body_com_z,left_ankle_x,left_ankle_y,left_ankle_z",
                        "0,1.0,2.0,3.0,4.0,5.0,6.0",
                        "1,1.1,2.1,3.1,4.1,5.1,6.1",
                    ]
                ),
                encoding="utf-8",
            )

            df = load_pose3d_long(csv_path, fps=30.0)

            self.assertEqual(len(df), 4)
            self.assertEqual(set(df["joint_name"]), {"body_com", "left_ankle"})
            self.assertEqual(df[df["joint_name"] == "body_com"]["x"].tolist(), [1.0, 1.1])
            self.assertEqual(df["time_s"].max(), 1 / 30.0)

    def test_load_pose3d_long_reindexes_sparse_source_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "pose3d_abs.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "frame_id,joint_name,x,y,z",
                        "0,body_com,0,0,0",
                        "3,body_com,1,0,0",
                    ]
                ),
                encoding="utf-8",
            )

            df = load_pose3d_long(csv_path, fps=30.0)

            self.assertEqual(df["source_frame_id"].tolist(), [0, 3])
            self.assertEqual(df["frame_id"].tolist(), [0, 1])
            self.assertEqual(df["time_s"].tolist(), [0.0, 1 / 30.0])


if __name__ == "__main__":
    unittest.main()
