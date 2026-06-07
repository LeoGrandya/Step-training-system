"""Business API tests for the /api/v1 MySQL-backed modules."""

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
from backend.models import (  # noqa: E402
    Account,
    AccountRole,
    AnalysisJob,
    FootworkType,
    KinematicsDataset,
    KinematicsFrameMetric,
    Permission,
    RouteDefinition,
    Role,
    RolePermission,
    Subject,
    TrainingConfig,
    TrainingVideo,
)
from backend.route_identity import route_active_name_sequence_hash  # noqa: E402

HTTP_NOT_IMPLEMENTED = 500 + 1


class ApiV1BusinessTest(unittest.TestCase):
    def setUp(self) -> None:
        app = Flask(__name__)
        app.config.update(
            TESTING=True,
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
        self._seed_base_rows()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _seed_base_rows(self) -> None:
        db.session.add_all(
            [
                Subject(id="sub_1", name="Alice", hand="right", years=2, level="amateur"),
                Subject(id="sub_2", name="Bob", hand="left", years=1, level="amateur"),
                FootworkType(id="fw_1", code="side", name="Side step"),
                FootworkType(id="fw_2", code="cross", name="Cross step"),
            ]
        )
        db.session.commit()

    def _seed_role(self, role_id: str = "role_1", code: str = "coach") -> Role:
        role = Role(id=role_id, code=code, name=f"{code.title()} role")
        db.session.add(role)
        db.session.commit()
        return role

    def _seed_permission(self, permission_id: str = "perm_1", code: str = "training.read") -> Permission:
        permission = Permission(id=permission_id, code=code, name=f"{code} permission")
        db.session.add(permission)
        db.session.commit()
        return permission

    def _seed_account(self, account_id: str = "acct_1", username: str = "coach") -> Account:
        account = Account(
            id=account_id,
            username=username,
            password_hash="sha256:test",
            display_name=f"{username.title()} User",
            status="active",
        )
        db.session.add(account)
        db.session.commit()
        return account

    def _seed_route(
        self,
        route_id: str = "route_1",
        *,
        footwork_type_id: str = "fw_1",
        name: str = "Seed route",
        sequence: str = "1,2,3",
    ) -> RouteDefinition:
        name_norm = name.lower()
        route = RouteDefinition(
            id=route_id,
            footwork_type_id=footwork_type_id,
            name=name,
            name_norm=name_norm,
            sequence=sequence,
            sequence_canon=sequence,
            active_name_sequence_hash=route_active_name_sequence_hash(name_norm, sequence),
            start_cell=5,
            rhythm_json={"defaultMs": 800},
            action_requirements="Keep balance",
            is_custom=True,
            is_active=True,
        )
        db.session.add(route)
        db.session.commit()
        return route

    def _seed_training_config(self, config_id: str = "cfg_1") -> TrainingConfig:
        if RouteDefinition.query.filter_by(id="route_1").first() is None:
            self._seed_route("route_1")
        config = TrainingConfig(
            id=config_id,
            subject_id="sub_1",
            footwork_type_id="fw_1",
            route_definition_id="route_1",
            mode="eval",
            analysis_profile="fast",
            light_duration_ms=500,
            step_interval_ms=900,
            loop_count=3,
            full_table_step_count=12,
            hardware_feedback=False,
            config_snapshot={"source": "test"},
        )
        db.session.add(config)
        db.session.commit()
        return config

    def _seed_video(self, video_id: str = "vid_1", config_id: str | None = None) -> TrainingVideo:
        video = TrainingVideo(
            id=video_id,
            subject_id="sub_1",
            training_config_id=config_id,
            left_video_path="D:/videos/left.mp4",
            right_video_path="D:/videos/right.mp4",
            left_original_name="left.mp4",
            right_original_name="right.mp4",
            left_size_bytes=100,
            right_size_bytes=120,
            stereo_params_path="D:/videos/stereo.json",
            probe_json={"fps": 60},
            status="uploaded",
        )
        db.session.add(video)
        db.session.commit()
        return video

    def _seed_dataset(self) -> KinematicsDataset:
        video = self._seed_video("vid_for_kin")
        job = AnalysisJob(
            job_id="job_1",
            subject_id="sub_1",
            training_video_id=video.id,
            status="done",
            progress=1.0,
        )
        dataset = KinematicsDataset(
            id="kin_1",
            job_id="job_1",
            subject_id="sub_1",
            training_video_id=video.id,
            report_payload_path="D:/jobs/job_1/report.json",
            chart_bundle_path="D:/jobs/job_1/chart.json",
            frame_csv_path="D:/jobs/job_1/frame_metrics.csv",
            session_csv_path="D:/jobs/job_1/session_summary.csv",
            step_csv_path="D:/jobs/job_1/step_metrics.csv",
            unit_csv_path="D:/jobs/job_1/unit_metrics.csv",
            summary_json={"score": 88},
            derived_stats_json={"speed": 1.2},
            quality_flags_json={"ok": True},
        )
        db.session.add_all(
            [
                job,
                dataset,
                KinematicsFrameMetric(
                    id=1,
                    dataset_id="kin_1",
                    frame_index=1,
                    time_s=0.01,
                    com_speed_mps=1.1,
                ),
                KinematicsFrameMetric(
                    id=2,
                    dataset_id="kin_1",
                    frame_index=5,
                    time_s=0.05,
                    com_speed_mps=1.5,
                ),
            ]
        )
        db.session.commit()
        return dataset

    def test_v1_get_endpoints_are_wired(self) -> None:
        for url in (
            "/api/v1/accounts",
            "/api/v1/roles",
            "/api/v1/permissions",
            "/api/v1/routes/missing/steps",
            "/api/v1/training-configs",
            "/api/v1/training-videos",
            "/api/v1/kinematics-datasets",
            "/api/v1/kinematics-datasets/missing/metrics",
            "/api/v1/evaluations",
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotEqual(response.status_code, HTTP_NOT_IMPLEMENTED)
                self.assertIn("ok", response.get_json())

    def test_role_crud_duplicate_code_and_permission_binding(self) -> None:
        permission = self.client.post("/api/v1/permissions", json={"code": " Training.Read ", "name": "Read"})
        self.assertEqual(200, permission.status_code)
        permission_id = permission.get_json()["item"]["id"]

        created = self.client.post("/api/v1/roles", json={"code": " Coach ", "name": "Coach"})
        self.assertEqual(200, created.status_code)
        role = created.get_json()["item"]
        self.assertEqual("coach", role["code"])

        duplicate = self.client.post("/api/v1/roles", json={"code": "coach", "name": "Other"})
        self.assertEqual(409, duplicate.status_code)
        self.assertEqual("duplicate_code", duplicate.get_json()["error"])

        listed = self.client.get("/api/v1/roles?keyword=coa&limit=10")
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, listed.get_json()["total"])

        updated = self.client.put(f"/api/v1/roles/{role['id']}", json={"name": "Head Coach"})
        self.assertEqual(200, updated.status_code)
        self.assertEqual("Head Coach", updated.get_json()["item"]["name"])
        self.assertEqual("coach", updated.get_json()["item"]["code"])

        bound = self.client.put(f"/api/v1/roles/{role['id']}/permissions", json={"permissionIds": [permission_id]})
        self.assertEqual(200, bound.status_code)
        self.assertEqual([permission_id], [item["id"] for item in bound.get_json()["items"]])

        permissions = self.client.get(f"/api/v1/roles/{role['id']}/permissions")
        self.assertEqual(200, permissions.status_code)
        self.assertEqual(1, permissions.get_json()["total"])

        deleted = self.client.delete(f"/api/v1/roles/{role['id']}")
        self.assertEqual(409, deleted.status_code)
        self.assertEqual("in_use", deleted.get_json()["error"])

    def test_permission_crud_duplicate_code_and_in_use_delete(self) -> None:
        role = self._seed_role("role_for_perm", "operator")
        created = self.client.post("/api/v1/permissions", json={"code": " Reports.View ", "name": "View reports"})
        self.assertEqual(200, created.status_code)
        permission = created.get_json()["item"]
        self.assertEqual("reports.view", permission["code"])

        duplicate = self.client.post("/api/v1/permissions", json={"code": "reports.view", "name": "Other"})
        self.assertEqual(409, duplicate.status_code)
        self.assertEqual("duplicate_code", duplicate.get_json()["error"])

        listed = self.client.get("/api/v1/permissions?keyword=reports&limit=10")
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, listed.get_json()["total"])

        updated = self.client.put(f"/api/v1/permissions/{permission['id']}", json={"name": "Reports read"})
        self.assertEqual(200, updated.status_code)
        self.assertEqual("Reports read", updated.get_json()["item"]["name"])

        db.session.add(RolePermission(role_id=role.id, permission_id=permission["id"]))
        db.session.commit()

        deleted = self.client.delete(f"/api/v1/permissions/{permission['id']}")
        self.assertEqual(409, deleted.status_code)
        self.assertEqual("in_use", deleted.get_json()["error"])

    def test_account_crud_duplicate_username_and_role_binding(self) -> None:
        role = self._seed_role("role_account", "analyst")
        created = self.client.post(
            "/api/v1/accounts",
            json={
                "username": " CoachA ",
                "passwordHash": "sha256:abc",
                "displayName": "Coach A",
                "status": "disabled",
            },
        )
        self.assertEqual(200, created.status_code)
        account = created.get_json()["item"]
        self.assertEqual("CoachA", account["username"])
        self.assertNotIn("passwordHash", account)

        duplicate = self.client.post(
            "/api/v1/accounts",
            json={"username": "CoachA", "passwordHash": "sha256:def", "displayName": "Other"},
        )
        self.assertEqual(409, duplicate.status_code)
        self.assertEqual("duplicate_username", duplicate.get_json()["error"])

        listed = self.client.get("/api/v1/accounts?keyword=coach&status=disabled&limit=10")
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, listed.get_json()["total"])

        updated = self.client.put(f"/api/v1/accounts/{account['id']}", json={"displayName": "Coach Alpha"})
        self.assertEqual(200, updated.status_code)
        self.assertEqual("Coach Alpha", updated.get_json()["item"]["displayName"])
        self.assertEqual("disabled", updated.get_json()["item"]["status"])

        bound = self.client.put(f"/api/v1/accounts/{account['id']}/roles", json={"roleIds": [role.id]})
        self.assertEqual(200, bound.status_code)
        self.assertEqual([role.id], [item["id"] for item in bound.get_json()["items"]])

        roles = self.client.get(f"/api/v1/accounts/{account['id']}/roles")
        self.assertEqual(200, roles.status_code)
        self.assertEqual(1, roles.get_json()["total"])

        deleted = self.client.delete(f"/api/v1/accounts/{account['id']}")
        self.assertEqual(200, deleted.status_code)
        self.assertEqual(404, self.client.get(f"/api/v1/accounts/{account['id']}").status_code)
        self.assertEqual(0, AccountRole.query.filter_by(account_id=account["id"]).count())

    def test_rbac_binding_invalid_ids_return_conflict(self) -> None:
        account = self._seed_account("acct_invalid", "invalid_user")
        role = self._seed_role("role_invalid", "invalid_role")

        invalid_roles = self.client.put(f"/api/v1/accounts/{account.id}/roles", json={"roleIds": ["missing"]})
        self.assertEqual(409, invalid_roles.status_code)
        self.assertEqual("invalid_reference", invalid_roles.get_json()["error"])

        invalid_permissions = self.client.put(
            f"/api/v1/roles/{role.id}/permissions",
            json={"permissionIds": ["missing"]},
        )
        self.assertEqual(409, invalid_permissions.status_code)
        self.assertEqual("invalid_reference", invalid_permissions.get_json()["error"])

    def test_subject_crud_list_keyword_detail_update_and_delete(self) -> None:
        created = self.client.post(
            "/api/v1/subjects",
            json={
                "name": "  Chen   Yanzhu  ",
                "age": 19,
                "heightCm": 171,
                "weightKg": 62.5,
                "hand": "left",
                "years": 3,
                "level": "pro",
            },
        )
        self.assertEqual(200, created.status_code)
        item = created.get_json()["item"]
        self.assertEqual("Chen Yanzhu", item["name"])

        listed = self.client.get("/api/v1/subjects?keyword=Yanzhu&limit=10")
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, listed.get_json()["total"])

        detail = self.client.get(f"/api/v1/subjects/{item['id']}")
        self.assertEqual(200, detail.status_code)
        self.assertEqual(item["id"], detail.get_json()["item"]["id"])

        updated = self.client.put(
            f"/api/v1/subjects/{item['id']}",
            json={"name": "Chen Yanzhu Jr", "level": "advanced"},
        )
        self.assertEqual(200, updated.status_code)
        updated_item = updated.get_json()["item"]
        self.assertEqual("Chen Yanzhu Jr", updated_item["name"])
        self.assertEqual(19, updated_item["age"])
        self.assertEqual(171, updated_item["heightCm"])
        self.assertEqual(62.5, updated_item["weightKg"])
        self.assertEqual(3, updated_item["years"])
        self.assertEqual("left", updated_item["hand"])
        self.assertEqual("advanced", updated_item["level"])

        deleted = self.client.delete(f"/api/v1/subjects/{item['id']}")
        self.assertEqual(200, deleted.status_code)
        self.assertEqual(404, self.client.get(f"/api/v1/subjects/{item['id']}").status_code)

    def test_footwork_type_crud_duplicate_code_and_soft_delete(self) -> None:
        payload = {
            "code": "  Ladder ",
            "name": "Ladder pattern",
            "category": "agility",
            "description": "Fast ladder movement",
            "defaultStartCell": 3,
            "defaultSequence": "1,2,3",
        }
        created = self.client.post("/api/v1/footwork-types", json=payload)
        self.assertEqual(200, created.status_code)
        item = created.get_json()["item"]
        self.assertEqual("ladder", item["code"])
        self.assertEqual(3, item["defaultStartCell"])

        duplicate = self.client.post("/api/v1/footwork-types", json={**payload, "name": "Other"})
        self.assertEqual(409, duplicate.status_code)
        self.assertEqual("duplicate_code", duplicate.get_json()["error"])

        listed = self.client.get("/api/v1/footwork-types?keyword=ladder&limit=10")
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, listed.get_json()["total"])

        detail = self.client.get(f"/api/v1/footwork-types/{item['id']}")
        self.assertEqual(200, detail.status_code)
        self.assertEqual(item["id"], detail.get_json()["item"]["id"])

        updated = self.client.put(
            f"/api/v1/footwork-types/{item['id']}",
            json={"code": "ladder-v2", "name": "Ladder pattern v2", "defaultStartCell": 4},
        )
        self.assertEqual(200, updated.status_code)
        self.assertEqual("ladder-v2", updated.get_json()["item"]["code"])
        self.assertEqual(4, updated.get_json()["item"]["defaultStartCell"])

        deleted = self.client.delete(f"/api/v1/footwork-types/{item['id']}")
        self.assertEqual(200, deleted.status_code)
        self.assertEqual(404, self.client.get(f"/api/v1/footwork-types/{item['id']}").status_code)

    def test_route_and_steps_crud_and_duplicate_route_conflict(self) -> None:
        payload = {
            "name": "Cross step",
            "sequence": "1,3,5",
            "startCell": 5,
            "footworkTypeId": "fw_1",
            "rhythm": {"defaultMs": 750},
            "actionRequirements": "Low center of gravity",
        }
        created = self.client.post("/api/v1/routes", json=payload)
        self.assertEqual(200, created.status_code)
        route = created.get_json()["item"]
        self.assertEqual("Cross step", route["name"])
        self.assertEqual({"defaultMs": 750}, route["rhythm"])

        duplicate = self.client.post("/api/v1/routes", json=payload)
        self.assertEqual(409, duplicate.status_code)
        self.assertEqual("duplicate_name_and_sequence", duplicate.get_json()["error"])

        route_id = route["id"]
        detail = self.client.get(f"/api/v1/routes/{route_id}")
        self.assertEqual(200, detail.status_code)
        self.assertEqual(route_id, detail.get_json()["item"]["id"])

        updated = self.client.put(
            f"/api/v1/routes/{route_id}",
            json={"name": "Cross step updated", "sequence": "1,3,5", "startCell": 4},
        )
        self.assertEqual(200, updated.status_code)
        self.assertEqual(4, updated.get_json()["item"]["startCell"])

        empty_steps = self.client.get(f"/api/v1/routes/{route_id}/steps")
        self.assertEqual(200, empty_steps.status_code)
        self.assertEqual(0, empty_steps.get_json()["total"])

        step_created = self.client.post(
            f"/api/v1/routes/{route_id}/steps",
            json={
                "stepOrder": 1,
                "cell": 3,
                "actionType": "move",
                "dwellMs": 200,
                "rhythmMs": 750,
                "note": "first move",
            },
        )
        self.assertEqual(200, step_created.status_code)
        step = step_created.get_json()["item"]
        self.assertEqual(3, step["cell"])

        step_updated = self.client.put(
            f"/api/v1/routes/{route_id}/steps/{step['id']}",
            json={"stepOrder": 1, "cell": 6, "note": "updated"},
        )
        self.assertEqual(200, step_updated.status_code)
        self.assertEqual(6, step_updated.get_json()["item"]["cell"])

        step_deleted = self.client.delete(f"/api/v1/routes/{route_id}/steps/{step['id']}")
        self.assertEqual(200, step_deleted.status_code)

        route_deleted = self.client.delete(f"/api/v1/routes/{route_id}")
        self.assertEqual(200, route_deleted.status_code)

        recreated = self.client.post("/api/v1/routes", json=payload)
        self.assertEqual(200, recreated.status_code)

    def test_training_config_crud(self) -> None:
        self._seed_route()
        created = self.client.post(
            "/api/v1/training-configs",
            json={
                "subjectId": "sub_1",
                "footworkTypeId": "fw_1",
                "routeDefinitionId": "route_1",
                "mode": "eval",
                "analysisProfile": "balanced",
                "lightDurationMs": 650,
                "stepIntervalMs": 950,
                "loopCount": 4,
                "hardwareFeedback": True,
                "configSnapshot": {"source": "api"},
            },
        )
        self.assertEqual(200, created.status_code)
        config_id = created.get_json()["item"]["id"]

        listed = self.client.get("/api/v1/training-configs?subjectId=sub_1&limit=10")
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, listed.get_json()["total"])

        detail = self.client.get(f"/api/v1/training-configs/{config_id}")
        self.assertEqual(200, detail.status_code)
        self.assertEqual("balanced", detail.get_json()["item"]["analysisProfile"])

        updated = self.client.put(
            f"/api/v1/training-configs/{config_id}",
            json={"mode": "test", "analysisProfile": "quality", "loopCount": 8},
        )
        self.assertEqual(200, updated.status_code)
        self.assertEqual("quality", updated.get_json()["item"]["analysisProfile"])

        deleted = self.client.delete(f"/api/v1/training-configs/{config_id}")
        self.assertEqual(200, deleted.status_code)
        self.assertEqual(404, self.client.get(f"/api/v1/training-configs/{config_id}").status_code)

    def test_training_config_rejects_route_footwork_mismatch(self) -> None:
        self._seed_route("route_2", footwork_type_id="fw_2", name="Other route", sequence="2,4,6")

        response = self.client.post(
            "/api/v1/training-configs",
            json={
                "subjectId": "sub_1",
                "footworkTypeId": "fw_1",
                "routeDefinitionId": "route_2",
            },
        )

        self.assertEqual(409, response.status_code)
        self.assertEqual("invalid_reference", response.get_json()["error"])

    def test_training_config_delete_returns_conflict_when_referenced(self) -> None:
        self._seed_training_config("cfg_video_ref")
        self._seed_video("vid_cfg_ref", config_id="cfg_video_ref")

        by_video = self.client.delete("/api/v1/training-configs/cfg_video_ref")
        self.assertEqual(409, by_video.status_code)
        self.assertEqual("in_use", by_video.get_json()["error"])

        self._seed_training_config("cfg_job_ref")
        db.session.add(AnalysisJob(job_id="job_cfg_ref", subject_id="sub_1", training_config_id="cfg_job_ref"))
        db.session.commit()

        by_job = self.client.delete("/api/v1/training-configs/cfg_job_ref")
        self.assertEqual(409, by_job.status_code)
        self.assertEqual("in_use", by_job.get_json()["error"])

    def test_training_video_list_detail_update_and_metadata_delete(self) -> None:
        video = self._seed_video("vid_1")

        listed = self.client.get("/api/v1/training-videos?subjectId=sub_1&keyword=left")
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, listed.get_json()["total"])

        detail = self.client.get(f"/api/v1/training-videos/{video.id}")
        self.assertEqual(200, detail.status_code)
        self.assertEqual("D:/videos/left.mp4", detail.get_json()["item"]["leftVideoPath"])

        updated = self.client.put(
            f"/api/v1/training-videos/{video.id}",
            json={"status": "analyzed", "probe": {"fps": 120}, "leftOriginalName": "new-left.mp4"},
        )
        self.assertEqual(200, updated.status_code)
        self.assertEqual("analyzed", updated.get_json()["item"]["status"])
        self.assertEqual({"fps": 120}, updated.get_json()["item"]["probe"])

        deleted = self.client.delete(f"/api/v1/training-videos/{video.id}")
        self.assertEqual(200, deleted.status_code)
        self.assertEqual(404, self.client.get(f"/api/v1/training-videos/{video.id}").status_code)

    def test_training_video_rejects_config_subject_mismatch(self) -> None:
        self._seed_training_config("cfg_for_sub_1")
        video = self._seed_video("vid_subject_update")

        response = self.client.put(
            f"/api/v1/training-videos/{video.id}",
            json={"subjectId": "sub_2", "trainingConfigId": "cfg_for_sub_1"},
        )

        self.assertEqual(409, response.status_code)
        self.assertEqual("invalid_reference", response.get_json()["error"])

    def test_training_video_delete_returns_conflict_when_referenced(self) -> None:
        self._seed_video("vid_job_ref")
        db.session.add(AnalysisJob(job_id="job_video_ref", subject_id="sub_1", training_video_id="vid_job_ref"))
        db.session.commit()

        by_job = self.client.delete("/api/v1/training-videos/vid_job_ref")
        self.assertEqual(409, by_job.status_code)
        self.assertEqual("in_use", by_job.get_json()["error"])

        self._seed_video("vid_dataset_ref")
        db.session.add_all(
            [
                AnalysisJob(job_id="job_dataset_ref", subject_id="sub_1"),
                KinematicsDataset(
                    id="kin_video_ref",
                    job_id="job_dataset_ref",
                    subject_id="sub_1",
                    training_video_id="vid_dataset_ref",
                ),
            ]
        )
        db.session.commit()

        by_dataset = self.client.delete("/api/v1/training-videos/vid_dataset_ref")
        self.assertEqual(409, by_dataset.status_code)
        self.assertEqual("in_use", by_dataset.get_json()["error"])

    def test_kinematics_dataset_list_detail_and_metrics(self) -> None:
        dataset = self._seed_dataset()

        listed = self.client.get(
            "/api/v1/kinematics-datasets"
            "?subjectId=sub_1&jobId=job_1&trainingVideoId=vid_for_kin&keyword=frame_metrics&limit=5"
        )
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, listed.get_json()["total"])

        detail = self.client.get(f"/api/v1/kinematics-datasets/{dataset.id}")
        self.assertEqual(200, detail.status_code)
        self.assertEqual({"score": 88}, detail.get_json()["item"]["summary"])

        metrics = self.client.get(f"/api/v1/kinematics-datasets/{dataset.id}/metrics?frameIndexFrom=2")
        self.assertEqual(200, metrics.status_code)
        body = metrics.get_json()
        self.assertEqual(1, body["total"])
        self.assertEqual(5, body["items"][0]["frameIndex"])

    def test_evaluation_crud_recalculates_grade(self) -> None:
        self._seed_route()
        dataset = self._seed_dataset()

        created = self.client.post(
            "/api/v1/evaluations",
            json={
                "subjectId": "sub_1",
                "analysisJobId": "job_1",
                "kinematicsDatasetId": dataset.id,
                "footworkTypeId": "fw_1",
                "routeDefinitionId": "route_1",
                "score": 82,
                "summary": {"balance": "stable"},
                "suggestions": ["increase tempo"],
            },
        )
        self.assertEqual(200, created.status_code)
        item = created.get_json()["item"]
        self.assertEqual("good", item["grade"])

        listed = self.client.get("/api/v1/evaluations?subjectId=sub_1&limit=10")
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, listed.get_json()["total"])

        updated = self.client.put(f"/api/v1/evaluations/{item['id']}", json={"score": 95})
        self.assertEqual(200, updated.status_code)
        self.assertEqual("excellent", updated.get_json()["item"]["grade"])

        detail = self.client.get(f"/api/v1/evaluations/{item['id']}")
        self.assertEqual(200, detail.status_code)
        self.assertEqual(95, detail.get_json()["item"]["score"])

        deleted = self.client.delete(f"/api/v1/evaluations/{item['id']}")
        self.assertEqual(200, deleted.status_code)
        self.assertEqual(404, self.client.get(f"/api/v1/evaluations/{item['id']}").status_code)

    def test_evaluation_rejects_cross_subject_job_dataset_mismatch(self) -> None:
        self._seed_route()
        self._seed_dataset()

        wrong_subject = self.client.post(
            "/api/v1/evaluations",
            json={
                "subjectId": "sub_2",
                "analysisJobId": "job_1",
                "kinematicsDatasetId": "kin_1",
                "footworkTypeId": "fw_1",
                "routeDefinitionId": "route_1",
                "score": 80,
            },
        )
        self.assertEqual(409, wrong_subject.status_code)
        self.assertEqual("invalid_reference", wrong_subject.get_json()["error"])

        db.session.add(AnalysisJob(job_id="job_2", subject_id="sub_1"))
        db.session.commit()

        wrong_job = self.client.post(
            "/api/v1/evaluations",
            json={
                "subjectId": "sub_1",
                "analysisJobId": "job_2",
                "kinematicsDatasetId": "kin_1",
                "footworkTypeId": "fw_1",
                "routeDefinitionId": "route_1",
                "score": 80,
            },
        )
        self.assertEqual(409, wrong_job.status_code)
        self.assertEqual("invalid_reference", wrong_job.get_json()["error"])

    def test_evaluation_rejects_route_footwork_mismatch(self) -> None:
        self._seed_dataset()
        self._seed_route("route_2", footwork_type_id="fw_2", name="Other route", sequence="2,4,6")

        response = self.client.post(
            "/api/v1/evaluations",
            json={
                "subjectId": "sub_1",
                "analysisJobId": "job_1",
                "kinematicsDatasetId": "kin_1",
                "footworkTypeId": "fw_1",
                "routeDefinitionId": "route_2",
                "score": 80,
            },
        )

        self.assertEqual(409, response.status_code)
        self.assertEqual("invalid_reference", response.get_json()["error"])

    def test_evaluation_rejects_job_config_route_footwork_mismatch(self) -> None:
        self._seed_route("route_1", footwork_type_id="fw_1", name="Route one", sequence="1,2,3")
        config = self._seed_training_config("cfg_eval_ref")
        db.session.add(
            AnalysisJob(
                job_id="job_cfg_eval",
                subject_id="sub_1",
                training_config_id=config.id,
                status="done",
                progress=1.0,
            )
        )
        db.session.commit()
        self._seed_route("route_2", footwork_type_id="fw_2", name="Route two", sequence="2,4,6")

        response = self.client.post(
            "/api/v1/evaluations",
            json={
                "subjectId": "sub_1",
                "analysisJobId": "job_cfg_eval",
                "footworkTypeId": "fw_2",
                "routeDefinitionId": "route_2",
                "score": 80,
            },
        )

        self.assertEqual(409, response.status_code)
        self.assertEqual("invalid_reference", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
