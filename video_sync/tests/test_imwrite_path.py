"""测试 Unicode 路径下的抽帧写图（不依赖真实视频）。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from video_sync.lib.sync import _write_image  # noqa: E402


class TestWriteImagePath(unittest.TestCase):
    def test_write_png_under_unicode_subdirectory(self) -> None:
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[:, :, 2] = 255
        params = [int(cv2.IMWRITE_PNG_COMPRESSION), 2]

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "测试输出" / "left"
            out_path = out_dir / "left_000000.png"
            self.assertTrue(_write_image(out_path, frame, ".png", params))
            self.assertTrue(out_path.is_file())
            self.assertGreater(out_path.stat().st_size, 0)

    def test_write_jpg_under_unicode_subdirectory(self) -> None:
        frame = np.full((32, 32, 3), 128, dtype=np.uint8)
        params = [int(cv2.IMWRITE_JPEG_QUALITY), 95]

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "输出" / "right_000001.jpg"
            self.assertTrue(_write_image(out_path, frame, ".jpg", params))
            self.assertGreater(out_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
