# 主脑：MySQL 基线与集成把关

> 你是全组的 schema 与接口契约负责人。其他人按表分工开发前，需先完成并评审本清单。

## 目标

统一 MySQL schema、Alembic 迁移流程、分页/响应格式、删除策略和模块边界，保证五人并行时不拆库、不拆 Flask 服务。

## 必读

- [数据库架构与开发约定](../数据库架构与开发约定.md)
- `web_1/backend/models.py`
- `web_1/migrations/versions/0001_initial_mysql_schema.py`
- `当前每个人的实际任务.md`（项目根目录）

## 负责范围

| 项 | 说明 |
|----|------|
| Schema 评审 | 他人提 migration 前你做 PR/合并评审 |
| Alembic | 空库 `alembic upgrade head` 可重复执行 |
| 统一分页 | 列表接口约定 `items/total/limit/offset` |
| 统一响应 | `ok` / `error` 不变 |
| 删除策略 | 软删 + RESTRICT，写入各成员任务边界 |
| 模块边界 | `backend/` 下按人划分子包或文件前缀，避免改他人表 |

## 当前基线（已完成）

- [x] `models.py` 17+ 业务表定义
- [x] `0001_initial_mysql_schema.py` 首版迁移
- [x] `0002_seed_footwork_types.py` 基础步伐种子数据
- [x] `db.py` + `v1.py` 启动绑定 MySQL
- [x] 分析任务状态同步：`JOB_STORE.set_status_writer` → `upsert_analysis_job_from_record`
- [x] `backend/api_utils.py` 统一分页与响应封装
- [x] `backend/delete_policy.py` 软删策略辅助
- [x] `backend/module_registry.py` + `backend/README_MODULES.md` 模块边界
- [x] `backend/api_v1/` 蓝图（meta/subjects/footwork-types/routes/training/analysis/evaluations/rbac 已接入）
- [x] 旧列表接口兼容分页：`/api/users`、`/api/custom-footworks`（无 `limit` 时仍全量）
- [x] `scripts/check_mysql_baseline.py` 本地基线检查
- [x] `test_mysql_migration_contract.py` + `test_api_utils.py` + `test_module_registry.py`
- [x] `docs/` 数据库约定与个人任务文档

## 待办（主脑 — 仅运维/集成）

1. **集成窗口**：按开发顺序组织联调（见下方顺序）。
2. **生产/共享 MySQL**：在真实空库执行 `alembic upgrade head`（可用 `python web_1/scripts/check_mysql_baseline.py --migrate --schema`）。

## 放行顺序（他人开工门槛）

| 顺序 | 谁可开工 | 门槛 |
|------|----------|------|
| 1 | 陈彦竹 | 空库迁移成功 + `subjects` 兼容策略书面确认 |
| 2 | 雷润华 | `footwork_types` 有种子或管理页可录入 |
| 3 | 金彦廷 | `route_definitions` 可读 + `subjects` 有数据 |
| 4 | 许婉其 | `training_videos` 上传可写路径 + pipeline 仍通 |
| 5 | 郝雨萱 | `kinematics_datasets` 有至少一条完整索引 |

## 验收

- 空 MySQL：`cd web_1; alembic upgrade head` 无报错
- 契约测试通过
- 旧前端 URL 未改、返回结构未破坏
- 全链路一条真实 job 从上传到报告可查

## 禁止

- 拆多个 Flask 服务或上 API Gateway
- 恢复 SQLite 业务库
- 未经评审直接改他人负责的表结构
