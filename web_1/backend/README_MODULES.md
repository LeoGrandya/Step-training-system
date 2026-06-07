# backend 模块边界

单 Flask 应用，业务按**表归属人**划分。改表结构须 Alembic migration + 主脑评审。

| 负责人 | 表 | 旧接口 | 新接口前缀 | 代码入口 |
|--------|-----|--------|------------|----------|
| 陈彦竹 | subjects, footwork_types | /api/users | /api/v1/subjects, /api/v1/footwork-types | api_v1/subjects.py, footwork_types.py |
| 雷润华 | route_definitions, route_steps | /api/custom-footworks | /api/v1/routes | api_v1/routes.py |
| 金彦廷 | training_*, accounts, roles, permissions | — | /api/v1/training-* | api_v1/training.py |
| 许婉其 | analysis_jobs, kinematics_* | /api/analysis/* | /api/v1/kinematics-datasets | backend/analysis/, api_v1/analysis.py |
| 郝雨萱 | evaluation_records, reports | /api/reports | /api/v1/evaluations | api_v1/evaluations.py |

共享（主脑维护）：`db.py`, `models.py`, `api_utils.py`, `delete_policy.py`, `module_registry.py`, `migrations/`.

机器可读清单：`GET /api/v1/meta/modules`。
