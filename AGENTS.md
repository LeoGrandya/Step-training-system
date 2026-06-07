# AGENTS.md — pose3d 双机位视频分析系统

## 项目概述

双机位视频分析系统，将左右机位视频转为可视化运动学结果。

分析链路：`上传视频 → 视频同步 → 3D重建 → 运动学计算 → 结果聚合 → 前端图表与CSV下载`

## 技术栈

- **后端**：Python 3.10+ / Flask / OpenCV / MediaPipe / pandas / numpy / scipy
- **前端**：Vue 3 + Vite（SPA 源码在 `frontend/`，构建产物到 `web_1/static/spa/`）
- **旧版页面**：vanilla JS + HTML（`web_1/static/js/`、`site/` 目录，通过 iframe 加载）
- **包管理**：pip（Python）、npm（前端）

## 目录结构

```
pose3d_project_3.0/
├── web_1/                          # 主应用（前后端一体，Flask 托管）
│   ├── v1.py                       # Flask 入口，所有 API 路由（薄路由，业务在 backend/）
│   ├── backend/analysis/           # 分析后端核心
│   │   ├── jobs.py                 # 任务状态与目录结构（JobStore + JobRecord）
│   │   ├── executor.py             # 线程池 + 队列调度（AnalysisExecutor）
│   │   ├── pipeline_runner.py      # 主编排：sync → pose3d → kinematics → result
│   │   ├── sync_service.py         # 对接 video_sync 模块
│   │   ├── pose3d_service.py       # 对接 pose3d_project_2.0_fixed 模块
│   │   ├── kinematics_service.py   # 对接运动学计算模块
│   │   ├── universal2_compat.py    # 生成 4 份 legacy CSV
│   │   ├── result_builder.py       # CSV/XLSX → 前端 result JSON
│   │   ├── results_store.py        # 历史结果索引持久化
│   │   ├── artifact_cache.py       # 阶段产物缓存（sync/pose3d）
│   │   ├── perf_metrics.py         # 性能指标写入
│   │   └── analysis_profiles.py    # 分析档位配置（fast/balanced/quality）
│   ├── static/spa/                 # Vue 构建产物（npm run build 后生成）
│   ├── jobs/                       # 每次分析任务目录（.gitignore 忽略）
│   └── data/                       # 运行时日志/旧历史索引；业务数据迁移到 MySQL
├── frontend/                       # Vue 3 SPA 源码（Vite）
│   └── src/
│       ├── views/                  # 页面组件（TrainingView, AuthView 等）
│       ├── components/             # 通用组件（SiteNav, TrainingGrid 等）
│       ├── services/               # API 调用 + 业务逻辑
│       ├── stores/                 # 状态管理（localStorage 封装）
│       ├── router/                 # Vue Router 配置
│       └── guides/                 # driver.js 用户引导
├── pose3d_project_2.0_fixed/       # 3D 姿态重建模块（独立 Python 包）
│   └── pose3d_pkg/
│       ├── calibration/            # 立体标定
│       ├── detection/              # 2D 姿态检测（MediaPipe）
│       ├── triangulation/          # 3D 三角测量 + 时序滤波
│       ├── io/                     # 视频读写 + CSV 输出
│       ├── viz/                    # 可视化（动画 + ParaView 导出）
│       └── cli/                    # 命令行入口
├── video_sync/                     # 双机位音频同步模块
├── requirements.txt                # 全仓库依赖（含 streamlit 等）
└── web_1/requirements.txt          # 主站最小依赖（日常开发推荐）
```

## 工程约定

### 命名
- Python：模块小写+下划线，类 PascalCase，函数/变量 snake_case
- Vue：组件 PascalCase，composables camelCase，目录/路由 kebab-case
- 前端跨文件共享配置挂到 `window`（如 `__WEB1_MAX_COMPARE_REPORTS__`），避免 magic string

### 分层
- `v1.py` 只做路由，业务逻辑全部在 `backend/analysis/` 下
- 复杂分支优先提前返回，减少深层嵌套
- 每个 `.py` 模块文件开头写一行简短 module docstring 说明职责

### API 约定
- JSON 请体使用 `request.get_json(silent=True)`，`None` 或非 `dict` 时返回 `400` + `{"ok": false, "error": "..."}`
- 成功统一带 `"ok": true`，失败统一带 `"ok": false` + `"error"` 字符串
- 文件下载白名单：`ANALYSIS_ARTIFACTS` frozenset，只允许四份 CSV 文件名

### 性能
- 已有 `ArtifactCache`（阶段产物缓存）、`scheduleSave`（防抖上报）、下载文件名白名单等机制，扩展时沿用同类模式
- 无测量数据前不盲目改算法阶数

### 前端
- 旧版 JS（`static/js/`）按 `index.html` 中 `<script defer>` 声明顺序执行
- 图表使用原生 canvas 绘制（非 ECharts/Chart.js）
- localStorage 键：`web1_max_compare_reports`（历史报告对比上限）
- 前端不直接读 CSV，所有图表数据来自 `GET /api/analysis/jobs/<job_id>/result` 返回的 JSON

### 环境变量
- `ANALYSIS_MAX_WORKERS`：分析并发数
- `ANALYSIS_MAX_QUEUE`：队列容量
- `ANALYSIS_KEEP_INPUT_VIDEOS`：保留输入视频
- `ANALYSIS_KEEP_SYNC_VIDEOS`：保留同步后视频
- `ANALYSIS_KEEP_INTERMEDIATES`：保留 pose3d 中间产物
- `KINEMATICS_EXPORT_PLOT_JSON`：保留 kinematics 绘图 JSON

## 常用命令

### 生产模式启动（推荐）
```powershell
# 1. 构建前端
cd frontend
npm.cmd run build

# 2. 启动 Flask
cd ..\web_1
python v1.py
# 访问 http://127.0.0.1:5000
```

### 开发模式启动
```powershell
# 终端1：Flask 后端
cd web_1
python v1.py

# 终端2：Vite 前端（带 API 代理）
cd frontend
npm.cmd run dev
# 访问 http://127.0.0.1:5173
```

### 安装依赖
```powershell
# 最小依赖（推荐）
python -m pip install -r .\web_1\requirements.txt

# 全仓库依赖（含 streamlit 等）
python -m pip install -r .\requirements.txt

# 前端依赖
cd frontend; npm.cmd install
```

### 验证
```powershell
# 前端构建 + 测试
cd frontend
npm.cmd test
npm.cmd run build

# 后端启动前检查
ffmpeg -version          # ffmpeg 必须可直接调用
python -c "import openpyxl"  # xlsx 导出依赖
```

### 清理项目体积
打包/迁移前可安全删除：`web_1/jobs/`、`__pycache__/`、`.venv/`、`_archive/`、`node_modules/`。

`web_1/data/app.db` 是旧 SQLite 业务库，本次迁移后不再作为业务数据来源；打包/迁移前可删除。MySQL 业务库通过 Alembic 管理 schema，连接信息来自环境变量。

## 建议阅读顺序（新人上手）

1. `项目必读readme.md` — 项目全貌
2. `web_1/v1.py` — 所有 API 入口
3. `web_1/backend/analysis/pipeline_runner.py` — 主分析流程编排
4. `web_1/backend/analysis/result_builder.py` — 前端数据来源
5. `web_1/static/js/analysis-dashboard.js` — 前端分析面板（如存在）
6. `README_后端.md` — 后端架构与 CSV 数据流
7. `README_前端.md` — 前端架构与图表对接
