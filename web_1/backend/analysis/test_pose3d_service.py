"""Regression tests for web-to-pose3d batch input adaptation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from .pose3d_service import build_user_settings, prepare_batch_job_videos, repo_root


class Pose3dBatchInputTests(unittest.TestCase):
    def test_prepare_batch_job_videos_creates_new_pose3d_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left_src = root / "left_aligned.mp4"
            right_src = root / "right_aligned.mp4"
            stereo_src = root / "stereo_params.json"
            data_root = root / "pose3d_data"
            left_src.write_bytes(b"left-video")
            right_src.write_bytes(b"right-video")
            stereo_src.write_text('{"ok": true}', encoding="utf-8")

            pair = prepare_batch_job_videos(
                job_id="job_123",
                synced_left=left_src,
                synced_right=right_src,
                data_root=data_root,
                stereo_src=stereo_src,
                log_fn=lambda _line: None,
            )

            self.assertEqual(pair["group"], "web_jobs")
            self.assertEqual(pair["person"], "job_123")
            self.assertEqual(pair["file_stem"], "analysis")
            self.assertEqual(pair["pair_name"], "web_jobs_job_123_analysis")
            self.assertEqual(Path(pair["left_video"]).read_bytes(), b"left-video")
            self.assertEqual(Path(pair["right_video"]).read_bytes(), b"right-video")
            self.assertTrue((data_root / "web_jobs" / "stereo_params.json").exists())
            self.assertTrue((data_root / "web_jobs" / "job_123" / "left" / "analysis.mp4").exists())
            self.assertTrue((data_root / "web_jobs" / "job_123" / "right" / "analysis.mp4").exists())

    def test_pose3d_cli_passes_frame_stride_to_detector(self) -> None:
        source = (
            repo_root()
            / "pose3d_project_2.0_fixed"
            / "pose3d_pkg"
            / "cli"
            / "run_pipeline.py"
        ).read_text(encoding="utf-8")

        self.assertIn("frame_stride", source)
        self.assertIn("extract_pose2d_from_stereo_videos(", source)
        self.assertIn("frame_stride=int(detector_cfg.get(\"frame_stride\") or 1)", source)
        self.assertIn("pose2d_progress_callback", source)
        self.assertIn("progress_callback=progress_callback", source)

    def test_build_user_settings_uses_new_batch_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_dir = repo_root() / "pose3d_project_2.0_fixed" / "models"
            self.assertTrue((model_dir / "pose_landmarker_full.task").exists())

            settings = build_user_settings(
                data_root=root / "data",
                output_root=root / "out",
                groups=["web_jobs"],
                detector_max_frames=None,
                frame_stride=3,
            )

            self.assertEqual(settings["input"]["data_root"], str(root / "data"))
            self.assertEqual(settings["input"]["output_root"], str(root / "out"))
            self.assertEqual(settings["input"]["groups"], ["web_jobs"])
            self.assertEqual(settings["detector"]["frame_stride"], 3)
            self.assertNotIn("session_dir", settings["input"])


if __name__ == "__main__":
    unittest.main()
