"""Regression tests for API v1 auth and training video creation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from flask import Flask

WEB1 = Path(__file__).resolve().parents[1]
if str(WEB1) not in sys.path:
    sys.path.insert(0, str(WEB1))

from backend.api_v1 import api_v1  # noqa: E402
from backend.db import db  # noqa: E402
from backend.models import Subject  # noqa: E402


class ApiV1RegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        app = Flask(__name__)
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            API_V1_RBAC_ENABLED=False,
        )
        db.init_app(app)
        app.register_blueprint(api_v1)
        self.app = app
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_registered_account_can_login_immediately(self) -> None:
        registered = self.client.post(
            "/api/v1/auth/register",
            json={"account": "coach_1", "username": "Coach One", "password": "pass1234"},
        )
        self.assertEqual(200, registered.status_code)

        logged_in = self.client.post(
            "/api/v1/auth/login",
            json={"account": "coach_1", "password": "pass1234"},
        )

        self.assertEqual(200, logged_in.status_code)
        body = logged_in.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual("coach_1", body["item"]["account"])

    def test_training_video_can_be_created_from_json_metadata(self) -> None:
        db.session.add(Subject(id="sub_1", name="Alice", hand="right", years=2, level="amateur"))
        db.session.commit()

        created = self.client.post(
            "/api/v1/training-videos",
            json={
                "subjectId": "sub_1",
                "leftVideoPath": "D:/videos/left.mp4",
                "rightVideoPath": "D:/videos/right.mp4",
                "leftOriginalName": "left.mp4",
                "rightOriginalName": "right.mp4",
                "leftSizeBytes": 100,
                "rightSizeBytes": 120,
                "stereoParamsPath": "D:/videos/stereo.json",
                "probe": {"fps": 60},
                "status": "uploaded",
            },
        )

        self.assertEqual(200, created.status_code)
        item = created.get_json()["item"]
        self.assertEqual("sub_1", item["subjectId"])
        self.assertEqual("D:/videos/left.mp4", item["leftVideoPath"])
        self.assertEqual("uploaded", item["status"])

        fetched = self.client.get(f"/api/v1/training-videos/{item['id']}")
        self.assertEqual(200, fetched.status_code)
        self.assertEqual({"fps": 60}, fetched.get_json()["item"]["probe"])


if __name__ == "__main__":
    unittest.main()
