"""Contract tests for the MySQL migration surface."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import re
import sqlite3
import unittest


ROOT = Path(__file__).resolve().parents[2]


class MySQLMigrationContractTest(unittest.TestCase):
    def _function_source(self, relative: str, function_name: str) -> str:
        source = (ROOT / relative).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                return ast.get_source_segment(source, node) or ""
        self.fail(f"{function_name} not found in {relative}")

    def _load_module_from_path(self, relative: str):
        path = ROOT / relative
        spec = importlib.util.spec_from_file_location(path.stem, path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _route_memory_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.execute(
            """
            CREATE TABLE route_definitions (
                id TEXT PRIMARY KEY,
                name_norm TEXT NOT NULL,
                sequence_canon TEXT NOT NULL,
                active_name_sequence_hash TEXT UNIQUE,
                is_active INTEGER NOT NULL
            )
            """
        )
        return conn

    def test_requirements_declare_mysql_migration_dependencies(self) -> None:
        requirements = (ROOT / "web_1" / "requirements.txt").read_text(encoding="utf-8")

        for package in ("Flask-SQLAlchemy", "PyMySQL", "alembic"):
            with self.subTest(package=package):
                self.assertIn(package, requirements)

    def test_model_file_defines_required_mysql_tables(self) -> None:
        source = (ROOT / "web_1" / "backend" / "models.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        table_names: set[str] = set()

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if (
                    isinstance(item, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in item.targets)
                    and isinstance(item.value, ast.Constant)
                    and isinstance(item.value.value, str)
                ):
                    table_names.add(item.value.value)

        expected = {
            "subjects",
            "accounts",
            "roles",
            "permissions",
            "account_roles",
            "role_permissions",
            "footwork_types",
            "route_definitions",
            "route_steps",
            "training_configs",
            "training_videos",
            "analysis_jobs",
            "kinematics_datasets",
            "kinematics_frame_metrics",
            "evaluation_records",
            "reports",
        }
        self.assertTrue(expected.issubset(table_names), sorted(expected - table_names))

    def test_initial_alembic_migration_creates_required_tables(self) -> None:
        migration = ROOT / "web_1" / "migrations" / "versions" / "0001_initial_mysql_schema.py"
        source = migration.read_text(encoding="utf-8")

        for table in (
            "subjects",
            "route_definitions",
            "training_videos",
            "analysis_jobs",
            "kinematics_datasets",
            "evaluation_records",
            "reports",
        ):
            with self.subTest(table=table):
                self.assertRegex(source, rf'op\.create_table\(\s*"{re.escape(table)}"')

    def test_sqlite_runtime_code_was_removed_from_core_paths(self) -> None:
        for relative in ("web_1/v1.py", "web_1/backend/analysis/report_persistence.py"):
            with self.subTest(path=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertNotIn("import sqlite3", source)
                self.assertNotIn("sqlite3.", source)

    def test_task_document_lists_every_person_and_acceptance_boundary(self) -> None:
        doc = (ROOT / "当前每个人的实际任务.md").read_text(encoding="utf-8")

        for name in ("陈彦竹", "雷润华", "金彦廷", "许婉其", "郝雨萱"):
            with self.subTest(name=name):
                self.assertIn(name, doc)

        for phrase in ("负责表", "负责接口", "前端页面", "不能改动的边界", "验收标准"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, doc)

    def test_seed_footwork_types_migration_exists(self) -> None:
        migration = ROOT / "web_1" / "migrations" / "versions" / "0002_seed_footwork_types.py"
        self.assertTrue(migration.is_file())
        source = migration.read_text(encoding="utf-8")
        self.assertIn("fw_side_step", source)
        self.assertIn("跨步", source)
        self.assertIn("context.is_offline_mode()", source)
        self.assertLess(source.index("context.is_offline_mode()"), source.index("op.get_bind()"))

    def test_brain_baseline_modules_exist(self) -> None:
        for relative in (
            "web_1/backend/api_utils.py",
            "web_1/backend/delete_policy.py",
            "web_1/backend/module_registry.py",
            "web_1/backend/api_v1/__init__.py",
            "web_1/scripts/check_mysql_baseline.py",
        ):
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file(), relative)

    def test_v1_registers_api_v1_blueprint(self) -> None:
        source = (ROOT / "web_1" / "v1.py").read_text(encoding="utf-8")
        self.assertIn("register_blueprint(api_v1)", source)
        self.assertIn("/api/v1", (ROOT / "web_1" / "backend" / "api_v1" / "__init__.py").read_text(encoding="utf-8"))

    def test_route_definition_unique_key_uses_short_active_hash(self) -> None:
        models = (ROOT / "web_1" / "backend" / "models.py").read_text(encoding="utf-8")
        migration = (ROOT / "web_1" / "migrations" / "versions" / "0001_initial_mysql_schema.py").read_text(
            encoding="utf-8"
        )

        for source in (models, migration):
            with self.subTest(source="route_unique_contract"):
                self.assertNotIn('UniqueConstraint("name_norm", "sequence_canon"', source)
                self.assertIn("active_name_sequence_hash", source)

        self.assertRegex(
            models,
            r'UniqueConstraint\("active_name_sequence_hash",\s*name="uq_route_definitions_active_name_sequence_hash"\)',
        )
        self.assertRegex(
            models,
            r"active_name_sequence_hash\s*=\s*db\.Column\(db\.String\(64\),\s*nullable=True\)",
        )
        self.assertIn('sa.Column("active_name_sequence_hash", sa.String(length=64), nullable=True)', migration)
        self.assertIn(
            'sa.UniqueConstraint("active_name_sequence_hash", name="uq_route_definitions_active_name_sequence_hash")',
            migration,
        )

    def test_models_use_text_backed_json_not_native_db_json(self) -> None:
        source = (ROOT / "web_1" / "backend" / "models.py").read_text(encoding="utf-8")

        self.assertNotIn("db.JSON", source)
        self.assertIn("JsonText", source)

    def test_json_text_helpers_roundtrip_dicts_and_lists(self) -> None:
        module = self._load_module_from_path("web_1/backend/json_text.py")

        for payload in ({"score": 91, "tags": ["fast", "stable"]}, [{"frame": 1}, {"frame": 2}]):
            with self.subTest(payload_type=type(payload).__name__):
                encoded = module.encode_json_text(payload)
                self.assertIsInstance(encoded, str)
                self.assertEqual(module.decode_json_text(encoded), payload)

        self.assertIsNone(module.encode_json_text(None))
        self.assertIsNone(module.decode_json_text(None))

    def test_route_identity_hash_supports_soft_delete_and_recreate(self) -> None:
        module = self._load_module_from_path("web_1/backend/route_identity.py")

        first = type("Route", (), {})()
        second = type("Route", (), {})()
        active_hash = module.route_active_name_sequence_hash("cross-step", "1,3,5")
        self.assertEqual(len(active_hash), 64)

        module.apply_active_route_identity(first, name_norm="cross-step", sequence_canon="1,3,5")
        self.assertEqual(first.active_name_sequence_hash, active_hash)
        module.clear_active_route_identity(first)
        self.assertIsNone(first.active_name_sequence_hash)

        module.apply_active_route_identity(second, name_norm="cross-step", sequence_canon="1,3,5")
        self.assertEqual(second.active_name_sequence_hash, active_hash)
        self.assertNotEqual(
            module.route_active_name_sequence_hash("cross-step1", "3,5"),
            module.route_active_name_sequence_hash("cross-step", "1,3,5"),
        )

    def test_route_hash_unique_key_allows_recreate_after_soft_delete(self) -> None:
        module = self._load_module_from_path("web_1/backend/route_identity.py")
        conn = self._route_memory_db()
        active_hash = module.route_active_name_sequence_hash("cross-step", "1,3,5")

        conn.execute(
            """
            INSERT INTO route_definitions
                (id, name_norm, sequence_canon, active_name_sequence_hash, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("r1", "cross-step", "1,3,5", active_hash, 1),
        )
        conn.execute(
            "UPDATE route_definitions SET active_name_sequence_hash = NULL, is_active = 0 WHERE id = ?",
            ("r1",),
        )
        conn.execute(
            """
            INSERT INTO route_definitions
                (id, name_norm, sequence_canon, active_name_sequence_hash, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("r2", "cross-step", "1,3,5", active_hash, 1),
        )

        rows = conn.execute(
            "SELECT id, active_name_sequence_hash, is_active FROM route_definitions ORDER BY id"
        ).fetchall()
        self.assertEqual([("r1", None, 0), ("r2", active_hash, 1)], rows)

    def test_route_hash_unique_key_rejects_two_active_duplicates(self) -> None:
        module = self._load_module_from_path("web_1/backend/route_identity.py")
        conn = self._route_memory_db()
        active_hash = module.route_active_name_sequence_hash("cross-step", "1,3,5")

        conn.execute(
            """
            INSERT INTO route_definitions
                (id, name_norm, sequence_canon, active_name_sequence_hash, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("r1", "cross-step", "1,3,5", active_hash, 1),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO route_definitions
                    (id, name_norm, sequence_canon, active_name_sequence_hash, is_active)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("r2", "cross-step", "1,3,5", active_hash, 1),
            )

    def test_route_task_doc_does_not_keep_old_composite_unique_requirement(self) -> None:
        doc = (ROOT / "docs" / "tasks" / "雷润华-训练路线与显示.md").read_text(encoding="utf-8")

        old_requirement_lines = [
            line
            for line in doc.splitlines()
            if "3." in line and "`name_norm` + `sequence_canon`" in line
        ]
        self.assertEqual([], old_requirement_lines)
        self.assertIn("active_name_sequence_hash VARCHAR(64) NULL UNIQUE", doc)

    def test_route_repository_uses_hash_for_duplicate_checks_and_soft_delete(self) -> None:
        create_source = self._function_source("web_1/backend/repositories.py", "create_custom_footwork_record")
        update_source = self._function_source("web_1/backend/repositories.py", "update_custom_footwork_record")
        delete_source = self._function_source("web_1/backend/repositories.py", "soft_delete_custom_footwork")

        for source in (create_source, update_source):
            with self.subTest(operation="create_or_update"):
                self.assertIn("route_active_name_sequence_hash", source)
                self.assertIn("RouteDefinition.active_name_sequence_hash", source)
                self.assertNotIn("RouteDefinition.name_norm == name", source)
                self.assertNotIn("RouteDefinition.sequence_canon == sequence_canon", source)

        self.assertIn("clear_active_route_identity(route)", delete_source)


if __name__ == "__main__":
    unittest.main()
