"""Tests for module ownership registry."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

WEB1 = Path(__file__).resolve().parents[1]
if str(WEB1) not in sys.path:
    sys.path.insert(0, str(WEB1))

from backend.module_registry import MODULES, owner_for_table  # noqa: E402


class ModuleRegistryTest(unittest.TestCase):
    def test_all_modules_have_owner(self) -> None:
        self.assertEqual(len(MODULES), 5)

    def test_subjects_owner(self) -> None:
        self.assertEqual(owner_for_table("subjects"), "陈彦竹")

    def test_analysis_jobs_owner(self) -> None:
        self.assertEqual(owner_for_table("analysis_jobs"), "许婉其")


if __name__ == "__main__":
    unittest.main()
