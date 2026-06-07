# 任务分发说明（给项目负责人）

## 文档清单

| 文档 | 读者 |
|------|------|
| [数据库架构与开发约定.md](./数据库架构与开发约定.md) | **全员必读** |
| [tasks/主脑-MySQL基线任务.md](./tasks/主脑-MySQL基线任务.md) | 你（主脑） |
| [tasks/陈彦竹-受试者与基础步伐.md](./tasks/陈彦竹-受试者与基础步伐.md) | 陈彦竹 |
| [tasks/雷润华-训练路线与显示.md](./tasks/雷润华-训练路线与显示.md) | 雷润华 |
| [tasks/金彦廷-训练配置视频与权限.md](./tasks/金彦廷-训练配置视频与权限.md) | 金彦廷 |
| [tasks/许婉其-分析任务与运动学索引.md](./tasks/许婉其-分析任务与运动学索引.md) | 许婉其 |
| [tasks/郝雨萱-训练效果评估与报告.md](./tasks/郝雨萱-训练效果评估与报告.md) | 郝雨萱 |
| 根目录 `当前每个人的实际任务.md` | 总览（可保留作 master 清单） |

## 推荐分发流程（分三步）

### 第一步：统一代码基线（不是只发 Markdown）

1. **仓库**：Git 远程（推荐）或压缩包；确保大家是**同一 commit**。
2. **环境说明**（群发一次）：
   - Python：`web_1/requirements.txt`
   - Node：`frontend` 下 `npm.cmd install`
   - MySQL 8 + 空库 `pose3d_project_3`
   - `ffmpeg` 在 PATH
   - 环境变量示例：`POSE3D_DATABASE_URL=mysql+pymysql://用户:密码@host:3306/pose3d_project_3?charset=utf8mb4`
3. **建库命令**（见《数据库架构与开发约定》2.2 节）。

只发任务 Markdown **不够**；没有同一套代码和空库迁移，接口会对不上表。

### 第二步：按人发文档

每人至少收到：

1. **《数据库架构与开发约定》**（全文）
2. **自己的 `docs/tasks/<姓名>-*.md`**
3. **开发顺序提醒**（见下）

可选：附带 `当前每个人的实际任务.md` 作总表。

### 第三步：协作规则

| 规则 | 说明 |
|------|------|
| 分支 | 每人 `feature/<姓名>-<模块>`，合并前你或主脑 review |
| Schema | 禁止私改生产库；改表走 Alembic + 你审批 |
| 联调顺序 | 陈彦竹 → 雷润华 → 金彦廷 → 许婉其 → 郝雨萱 |
| 周会验收 | 对照各人任务 md 里的 checkbox + 前端 `npm test/build` |

## 开发顺序（务必遵守）

```
主脑：迁移可跑、契约清晰
  ↓
陈彦竹：subjects + footwork_types
  ↓
雷润华：route_definitions + route_steps
  ↓
金彦廷：training_configs + training_videos + RBAC
  ↓
许婉其：analysis_jobs + kinematics_*
  ↓
郝雨萱：evaluation_records + reports
  ↓
全组：一条真实视频跑通全链路
```

## 常见误区

| 误区 | 正确做法 |
|------|----------|
| 只发任务 md，不发代码 | 先对齐 Git 仓库与 `alembic upgrade head` |
| 每人一个 Flask 服务 | 单 `v1.py`，按 `backend/` 模块分工 |
| 把视频塞进 MySQL BLOB | 只存路径，文件在 `jobs/` |
| 物理删除被引用的受试者 | 软删除 `is_active` / `deleted_at` |

## 首次开会建议议程（30 分钟）

1. 演示：空库迁移 + `python v1.py` 启动
2. 过一遍 ER 图（数据库文档第 4 节）
3. 确认每人负责表与**禁止改动**边界
4. 约定代码评审人与合并窗口（建议每周固定半天联调）
