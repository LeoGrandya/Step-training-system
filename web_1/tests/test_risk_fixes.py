"""Regression tests for known cross-module risk fixes."""

from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

from flask import Flask

WEB1 = Path(__file__).resolve().parents[1]
if str(WEB1) not in sys.path:
    sys.path.insert(0, str(WEB1))

from backend import repositories as repo  # noqa: E402
from backend.api_v1 import api_v1  # noqa: E402
from backend.db import db  # noqa: E402
from backend.models import (  # noqa: E402
    Account,
    AccountRole,
    FootworkType,
    KinematicsFrameMetric,
    Permission,
    Role,
    RolePermission,
    RouteDefinition,
    Subject,
    TrainingConfig,
    TrainingVideo,
)
from backend.route_identity import route_active_name_sequence_hash  # noqa: E402


class RiskFixTest(unittest.TestCase):
    def setUp(self) -> None:
        app = Flask(__name__)
        app.config.update(
            TESTING=True,
            API_V1_RBAC_ENABLED=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(app)
        app.register_blueprint(api_v1)
        self.app = app
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = app.test_client()
        self._seed_base()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _seed_base(self) -> None:
        db.session.add_all(
            [
                Subject(id="sub_1", name="Alice", hand="right", years=2, level="amateur"),
                FootworkType(id="fw_1", code="side", name="Side step"),
                RouteDefinition(
                    id="route_1",
                    footwork_type_id="fw_1",
                    name="Side route",
                    name_norm="side route",
                    sequence="1,5,9",
                    sequence_canon="1,5,9",
                    active_name_sequence_hash=route_active_name_sequence_hash("side route", "1,5,9"),
                    start_cell=5,
                    rhythm_json={"defaultMs": 880},
                    action_requirements="Keep low center",
                    is_custom=True,
                    is_active=True,
                ),
            ]
        )
        db.session.commit()

    def _seed_account_with_permission(self, permission_code: str = "subjects.write") -> Account:
        account = Account(id="acct_1", username="coach", password_hash="sha256:test", display_name="Coach")
        role = Role(id="role_1", code="coach", name="Coach")
        permission = Permission(id="perm_1", code=permission_code, name=permission_code)
        db.session.add_all([account, role, permission])
        db.session.commit()
        db.session.add_all(
            [
                AccountRole(account_id=account.id, role_id=role.id),
                RolePermission(role_id=role.id, permission_id=permission.id),
            ]
        )
        db.session.commit()
        return account

    def _seed_training_config(self) -> TrainingConfig:
        config = TrainingConfig(
            id="cfg_1",
            subject_id="sub_1",
            footwork_type_id="fw_1",
            route_definition_id="route_1",
            mode="eval",
            analysis_profile="fast",
        )
        db.session.add(config)
        db.session.commit()
        return config

    def test_rbac_write_requests_require_matching_account_permission(self) -> None:
        self._seed_account_with_permission("subjects.write")

        blocked = self.client.post("/api/v1/subjects", json={"name": "No Header"})
        self.assertEqual(403, blocked.status_code)
        self.assertEqual("permission_denied", blocked.get_json()["error"])

        allowed = self.client.post(
            "/api/v1/subjects",
            json={"name": "With Header"},
            headers={"X-Account-Id": "acct_1"},
        )
        self.assertEqual(200, allowed.status_code)
        self.assertEqual("With Header", allowed.get_json()["item"]["name"])

    def test_training_video_creation_can_link_to_training_config(self) -> None:
        self._seed_training_config()
        with tempfile.TemporaryDirectory() as tmp:
            left = Path(tmp) / "left.mp4"
            right = Path(tmp) / "right.mp4"
            left.write_bytes(b"left")
            right.write_bytes(b"right")

            video_id = repo.create_training_video_record(
                subject_id="sub_1",
                training_config_id="cfg_1",
                left_path=left,
                right_path=right,
                left_original_name="left-source.mp4",
                right_original_name="right-source.mp4",
                stereo_params_path=None,
                probe={"fps": 60},
            )

        video = TrainingVideo.query.filter_by(id=video_id).first()
        self.assertIsNotNone(video)
        self.assertEqual("cfg_1", video.training_config_id)

    def test_training_stats_endpoint_groups_configs_and_videos(self) -> None:
        self._seed_training_config()
        db.session.add(
            TrainingVideo(
                id="vid_1",
                subject_id="sub_1",
                training_config_id="cfg_1",
                left_video_path="left.mp4",
                right_video_path="right.mp4",
                status="uploaded",
            )
        )
        db.session.commit()

        response = self.client.get("/api/v1/training-stats")

        self.assertEqual(200, response.status_code)
        item = response.get_json()["item"]
        self.assertEqual(1, item["totals"]["trainingConfigs"])
        self.assertEqual(1, item["totals"]["trainingVideos"])
        self.assertEqual(1, item["configsByMode"]["eval"])
        self.assertEqual(1, item["videosByStatus"]["uploaded"])

    def test_kinematics_upsert_imports_sampled_frame_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kin_dir = Path(tmp)
            (kin_dir / "frame_metrics.csv").write_text(
                "frame_id,time_s,com_speed_mps,com_acceleration_mps2,turning_speed_deg_s,"
                "left_knee_angle_deg,right_knee_angle_deg,left_ankle_angle_deg,right_ankle_angle_deg\n"
                "1,0.01,1.1,2.2,3.3,40,41,20,21\n"
                "2,0.02,1.2,2.3,3.4,42,43,22,23\n",
                encoding="utf-8",
            )
            for name in ("session_summary.csv", "step_metrics.csv", "unit_metrics.csv"):
                (kin_dir / name).write_text("metric,value\n", encoding="utf-8")
            report_path = kin_dir / "report_payload.json"
            chart_path = kin_dir / "chart_bundle.json"
            report_path.write_text("{}", encoding="utf-8")
            chart_path.write_text("{}", encoding="utf-8")

            dataset_id = repo.upsert_kinematics_dataset_for_job(
                job_id="job_kin",
                subject_id="sub_1",
                training_video_id=None,
                report_path=report_path,
                chart_bundle_path=chart_path,
                kinematics_dir=kin_dir,
                payload={"summaryMetrics": {"score": 80}},
            )

        rows = KinematicsFrameMetric.query.filter_by(dataset_id=dataset_id).order_by(
            KinematicsFrameMetric.frame_index.asc()
        ).all()
        self.assertEqual(2, len(rows))
        self.assertEqual(1, rows[0].frame_index)
        self.assertAlmostEqual(1.1, rows[0].com_speed_mps)

    def test_custom_footworks_include_action_requirements_and_rhythm(self) -> None:
        payload = self.client.get("/api/v1/routes?keyword=Side").get_json()
        route = payload["items"][0]
        self.assertEqual("Keep low center", route["actionRequirements"])
        self.assertEqual({"defaultMs": 880}, route["rhythm"])

        items, total = repo.list_custom_footworks_page(keyword="Side", limit=10, offset=0)
        self.assertEqual(1, total)
        item = items[0]
        self.assertEqual("Keep low center", item["actionRequirements"])
        self.assertEqual({"defaultMs": 880}, item["rhythm"])


if __name__ == "__main__":
    unittest.main()
