#!/usr/bin/env python3
"""Run MySQL migration contract tests and optional live schema check."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEB1 = ROOT / "web_1"


def run_contract_tests() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "web_1.tests.test_mysql_migration_contract", "-v"],
        cwd=str(ROOT),
    )
    return int(proc.returncode)


def run_api_utils_tests() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "web_1.tests.test_api_utils", "web_1.tests.test_module_registry", "-v"],
        cwd=str(ROOT),
    )
    return int(proc.returncode)


def run_alembic_upgrade() -> int:
    env = os.environ.copy()
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(WEB1),
        env=env,
    )
    return int(proc.returncode)


def run_schema_check() -> int:
    sys.path.insert(0, str(WEB1))
    from v1 import app, validate_runtime_baseline

    os.environ["POSE3D_VALIDATE_DB"] = "1"
    validate_runtime_baseline()
    with app.app_context():
        from backend.runtime_checks import validate_mysql_schema

        validate_mysql_schema()
    print("MySQL schema check OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify pose3d MySQL baseline")
    parser.add_argument("--migrate", action="store_true", help="Run alembic upgrade head")
    parser.add_argument("--schema", action="store_true", help="Validate tables on live MySQL")
    args = parser.parse_args()

    code = run_contract_tests()
    if code != 0:
        return code
    code = run_api_utils_tests()
    if code != 0:
        return code
    if args.migrate:
        code = run_alembic_upgrade()
        if code != 0:
            return code
    if args.schema:
        try:
            code = run_schema_check()
        except Exception as exc:
            print(f"Schema check failed: {exc}", file=sys.stderr)
            return 1
        if code != 0:
            return code
    print("Baseline checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
