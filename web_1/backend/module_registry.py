"""Module ownership map: which teammate owns which tables and code paths."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleOwnership:
    owner: str
    tables: tuple[str, ...]
    legacy_routes: tuple[str, ...]
    v1_prefix: str
    backend_paths: tuple[str, ...]


MODULES: tuple[ModuleOwnership, ...] = (
    ModuleOwnership(
        owner="陈彦竹",
        tables=("subjects", "footwork_types"),
        legacy_routes=("/api/users",),
        v1_prefix="/api/v1/subjects",
        backend_paths=(
            "web_1/backend/repositories.py",
            "web_1/backend/api_v1/subjects.py",
            "web_1/backend/api_v1/footwork_types.py",
        ),
    ),
    ModuleOwnership(
        owner="雷润华",
        tables=("route_definitions", "route_steps"),
        legacy_routes=("/api/custom-footworks",),
        v1_prefix="/api/v1/routes",
        backend_paths=(
            "web_1/backend/repositories.py",
            "web_1/backend/api_v1/routes.py",
        ),
    ),
    ModuleOwnership(
        owner="金彦廷",
        tables=(
            "training_configs",
            "training_videos",
            "accounts",
            "roles",
            "permissions",
            "account_roles",
            "role_permissions",
        ),
        legacy_routes=(),
        v1_prefix="/api/v1/training-configs, /api/v1/accounts, /api/v1/roles, /api/v1/permissions",
        backend_paths=("web_1/backend/api_v1/training.py", "web_1/backend/api_v1/rbac.py"),
    ),
    ModuleOwnership(
        owner="许婉其",
        tables=("analysis_jobs", "kinematics_datasets", "kinematics_frame_metrics", "analysis_results"),
        legacy_routes=("/api/analysis/jobs", "/api/analysis/results"),
        v1_prefix="/api/v1/kinematics-datasets",
        backend_paths=(
            "web_1/backend/analysis/",
            "web_1/backend/api_v1/analysis.py",
        ),
    ),
    ModuleOwnership(
        owner="郝雨萱",
        tables=("evaluation_records", "reports"),
        legacy_routes=("/api/reports",),
        v1_prefix="/api/v1/evaluations",
        backend_paths=("web_1/backend/api_v1/evaluations.py",),
    ),
)


TABLE_OWNERS: dict[str, str] = {}
for module in MODULES:
    for table in module.tables:
        TABLE_OWNERS[table] = module.owner


def owner_for_table(table: str) -> str | None:
    return TABLE_OWNERS.get(table)


def modules_as_dicts() -> list[dict[str, object]]:
    return [
        {
            "owner": m.owner,
            "tables": list(m.tables),
            "legacyRoutes": list(m.legacy_routes),
            "v1Prefix": m.v1_prefix,
            "backendPaths": list(m.backend_paths),
        }
        for m in MODULES
    ]
