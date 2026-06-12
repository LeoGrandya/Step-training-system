# CLAUDE.md — pose3d 双机位视频分析系统

## 项目概述

双机位视频分析系统，将左右机位视频转为可视化运动学结果。

分析链路：`上传视频 → 视频同步 → 3D重建 → 运动学计算 → 结果聚合 → 前端图表与CSV下载`

## 技术栈

- **后端**：Python 3.10+ / Flask / OpenCV / MediaPipe / pandas / numpy / scipy
- **前端**：Vue 3 + Vite（SPA 源码在 `frontend/`，构建产物到 `web_1/static/spa/`）
- **旧版页面**：vanilla JS + HTML（`site/` 目录，通过 iframe 加载）
- **包管理**：pip（Python）、npm（前端）

## 目录结构

```
pose3d_project_4.0/
├── web_1/                          # 主应用（前后端一体，Flask 托管）
│   ├── v1.py                       # Flask 入口，所有 API 路由
│   ├── backend/                    # 业务逻辑
│   │   ├── analysis/               # 分析后端核心
│   │   │   ├── jobs.py             # 任务状态与目录结构（JobStore + JobRecord）
│   │   │   ├── executor.py         # 线程池 + 队列调度
│   │   │   ├── pipeline_runner.py  # 主编排：sync → pose3d → kinematics → result
│   │   │   ├── sync_service.py     # 对接 video_sync 模块
│   │   │   ├── pose3d_service.py   # 对接 pose3d_project_2.0_fixed 模块
│   │   │   ├── kinematics_service.py # 对接运动学计算模块
│   │   │   ├── result_builder.py   # CSV/XLSX → 前端 result JSON
│   │   │   ├── report_ui_builder.py # 旧版 report-ui 协议
│   │   │   ├── results_store.py    # 历史结果索引
│   │   │   ├── artifact_cache.py   # 阶段产物缓存
│   │   │   └── analysis_profiles.py # 分析档位（fast/balanced/quality）
│   │   ├── api_v1/                 # REST API（Blueprint 注册）
│   │   ├── db.py                   # SQLAlchemy + SQLite 初始化
│   │   ├── models.py               # ORM 模型
│   │   └── repositories.py         # 数据访问层
│   ├── static/spa/                 # Vue 构建产物（npm run build 生成，.gitignore）
│   ├── jobs/                       # 分析任务目录（.gitignore）
│   └── data/                       # SQLite DB + 历史结果索引
├── frontend/                       # Vue 3 SPA 源码（Vite + Tailwind CSS 4）
│   └── src/
│       ├── views/                  # 页面组件
│       │   ├── PingpongReportView.vue  # 分析报告页（my-pingpong-project 组件绑定）
│       │   ├── TrainingView.vue
│       │   ├── AnalysisView.vue
│       │   ├── DataManagementView.vue
│       │   └── ...
│       ├── components/
│       │   ├── report/             # 12 个 ECharts 报告组件（含 mock 降级）
│       │   └── ...                 # SiteNav, TrainingGrid 等
│       ├── services/               # API 调用 + reportAdapter（数据→ECharts options）
│       ├── stores/                 # localStorage 封装
│       ├── router/                 # Vue Router（hash 模式）
│       └── guides/                 # driver.js 用户引导
├── site/                           # 旧版静态 HTML 页面（legacy iframe）
├── pose3d_project_2.0_fixed/       # 3D 姿态重建（MediaPipe → 三角测量）
├── footwork_kinematics_universal2/ # 运动学分析（步态分割 + 指标计算）
├── video_sync/                     # 双机位音频同步
├── requirements.txt                # 全仓库依赖
└── web_1/requirements.txt          # 主站最小依赖（日常开发推荐）
```

## 工程约定

### 命名
- Python：模块小写+下划线，类 PascalCase，函数/变量 snake_case
- Vue：组件 PascalCase，composables camelCase，目录/路由 kebab-case

### 分层
- `v1.py` 只做路由，业务逻辑全部在 `backend/` 下
- 复杂分支优先提前返回，减少深层嵌套
- 每个 `.py` 模块文件开头写一行简短 module docstring

### API 约定
- JSON 请体使用 `request.get_json(silent=True)`，`None` 或非 `dict` 时返回 `400` + `{"ok": false, "error": "..."}`
- 成功统一带 `"ok": true`，失败统一带 `"ok": false` + `"error"` 字符串

### 前端
- 图表使用 ECharts 5.6（12 个 report 组件内联 echarts.init）
- 报告页数据流：`reportAdapter.js` 从 API 构建 ECharts options → props 注入组件 → 无数据时 mock 降级
- localStorage 键：`ai_sport_lab.*` 前缀

### 独立练习
- 与主业务无关的脚本放在 `examples/python/`
- 独立脚本产生的输出放在 `outputs/`

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | SQLite 自动路径 | 数据库连接。服务器部署必需 |
| `ANALYSIS_MAX_WORKERS` | `1` | 分析线程池大小 |
| `ANALYSIS_MAX_QUEUE` | `8` | 最大排队任务数 |
| `ANALYSIS_KEEP_INPUT_VIDEOS` | `1` | 保留原始上传视频 |
| `ANALYSIS_KEEP_SYNC_VIDEOS` | `0` | 保留同步后视频 |
| `ANALYSIS_KEEP_INTERMEDIATES` | `0` | 保留 pose3d 中间产物 |
| `KINEMATICS_EXPORT_PLOT_JSON` | `0` | 保留绘图 JSON |
| `FLASK_USE_RELOADER` | `0` | 生产环境应关闭 |

## 执行铁律

**方案执行前必须输出 TodoList**：列出所有步骤，每条附原因。TodoList 必须包含：
- **质量审查**：逐文件 diff 确认无遗漏
- **代码审查**：复用/简化/安全性检查
- **构建验证**：npm run build + Flask 启动 + 功能场景测试

执行时按 TodoList 顺序逐步推进，每完成一步标记 completed 后再开始下一步。

## 常用命令

### 生产模式启动
```powershell
cd frontend; npm.cmd run build
cd ..\web_1; python v1.py
# 访问 http://127.0.0.1:5000
```

### 开发模式启动
```powershell
# 终端1：Flask
cd web_1; python v1.py
# 终端2：Vite
cd frontend; npm.cmd run dev
# 访问 http://127.0.0.1:5173
```

### 安装依赖
```powershell
python -m pip install -r .\web_1\requirements.txt   # 最小依赖（推荐）
python -m pip install -r .\requirements.txt          # 全仓库依赖
cd frontend; npm.cmd install                         # 前端依赖
```

### 验证
```powershell
cd frontend; npm.cmd run build    # 前端构建
ffmpeg -version                   # ffmpeg 必须可直接调用
python -c "import openpyxl"       # xlsx 导出依赖
```

### 清理项目体积
打包/迁移前可安全删除：`web_1/jobs/`、`__pycache__/`、`.venv/`、`node_modules/`。

不要删除 `web_1/data/app.db`（业务数据），除非明确要重置系统。
