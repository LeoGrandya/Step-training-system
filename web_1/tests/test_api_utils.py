"""Tests for shared API pagination helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

WEB1 = Path(__file__).resolve().parents[1]
if str(WEB1) not in sys.path:
    sys.path.insert(0, str(WEB1))

from backend.api_utils import parse_bool_query, parse_pagination  # noqa: E402


class _Args(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class ApiUtilsTest(unittest.TestCase):
    def test_parse_bool_query(self) -> None:
        self.assertIs(parse_bool_query("true"), True)
        self.assertIs(parse_bool_query("0"), False)
        self.assertIsNone(parse_bool_query(None))

    def test_parse_pagination_defaults(self) -> None:
        page = parse_pagination(_Args(), default_limit=30)
        self.assertEqual(page.limit, 30)
        self.assertEqual(page.offset, 0)

    def test_parse_pagination_legacy_no_limit(self) -> None:
        page = parse_pagination(_Args(), default_limit=None)
        self.assertIsNone(page.limit)

    def test_parse_pagination_clamps_limit(self) -> None:
        page = parse_pagination(_Args({"limit": "9999"}), default_limit=30)
        self.assertEqual(page.limit, 200)

    def test_parse_pagination_keyword(self) -> None:
        page = parse_pagination(_Args({"keyword": " 张三 "}), default_limit=10)
        self.assertEqual(page.keyword, "张三")


if __name__ == "__main__":
    unittest.main()
