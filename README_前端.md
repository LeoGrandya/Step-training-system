# 前端 README（web_html + Vue SPA 迁移版）

## 1. 前端总体说明

当前前端由 **Vue 3 SPA + legacy 静态 HTML** 组成，统一由 Flask `web_1/v1.py` 托管：

- 入口：`GET /` → `web_1/static/spa/index.html`（需先在 `frontend/` 执行 `npm run build`）
- Legacy 页：`/legacy-html/*.html`（源码在 `pose3d_project_3.0/site/`）
- 静态资源：`/assets/*`（site/assets）、`/spa/*`（Vue 构建产物）
- 开发：Vite `frontend/` + Flask API 代理（见 `最小启动方式.md`）

旧版原生 JS 一体页（`templates/index.html` + `static/js/*`）已移至 `web_1/_deprecated/`。

---

## 2. 脚本加载顺序与 `window` 配置约定

`index.html` 底部脚本为 **defer**，按声明顺序执行；与全局训练/设置相关的核心顺序为：

`app-core.js` → `app-flow.js` → … → `app-init.js` → … → `analysis-dashboard.js`（靠后）。

- **`app-core.js`**：较早执行，负责参数设置侧栏绑定、训练运行时配置等；并向 `window` 暴露稳定元数据（例如 `__WEB1_MAX_COMPARE_REPORTS__`：含 `storageKey`、`min`、`max`、`defaultValue`），供后续脚本读取，避免多处硬编码同一常数。
- **`analysis-dashboard.js`**：依赖上述元数据；若元数据缺失则使用内置 fallback，避免脚本顺序异常时页面崩溃。

新增跨文件配置时，优先在 **先加载** 的脚本中挂到 `window`，后加载脚本只读。

---

## 3. 设置侧栏与历史报告对比上限

- **DOM**：`#settingsPanel` 内 `#cfgMaxCompareReports`（报告与对比：最多可选份数）。
- **持久化**：`localStorage` 键 **`web1_max_compare_reports`**（整数，默认 10，合法范围 2–30，由设置输入框 clamp）。
- **联动**：修改并失焦/变更后，`app-core.js` 写入 `localStorage` 并派发浏览器事件 **`web1:maxCompareReportsChanged`**；`analysis-dashboard.js` 监听后按新上限截断已选报告 ID，并刷新对比条文案「比对限 N 份…」。

详见 [`docs/项目代码梳理与僵尸文件.md`](docs/项目代码梳理与僵尸文件.md) 与 [`frontend/src/stores/storage.js`](frontend/src/stores/storage.js)（本地存储键）。

---

## 4. 前端目录结构与文件职责

```text
web_1/
├─ templates/
│  └─ index.html                    # 页面骨架（训练区 + 视频分析区）
├─ static/
│  ├─ css/
│  │  ├─ app.css
│  │  ├─ analysis-dashboard.css
│  │  └─ ui-enhancements.css
│  └─ js/
│     ├─ analysis-dashboard.js      # 视频分析核心（上传/轮询/图表/下载）
│     ├─ app-init.js                # 页面初始化入口
│     ├─ app-core.js                # 全局状态/工具函数
│     ├─ app-flow.js                # 训练流程与业务请求
│     ├─ training-mode-step.js      # 模式切换（eval/free/test）
│     ├─ step3-mode-adapter.js      # 流程衔接到视频分析
│     ├─ user-profile-step.js       # 用户基础信息采集
│     ├─ app-toolbar.js             # 顶部工具条逻辑
│     ├─ ui-enhancements.js         # 交互增强
│     ├─ tutorial-video.js          # 教学视频逻辑
│     └─ app.js                     # 兼容壳（已迁移提示）
```

---

## 5. 视频分析板块完整流程（前端视角）

主文件：`web_1/static/js/analysis-dashboard.js`

1. 用户选择左右视频（可选标定 JSON）
2. 前端组装 `FormData`，提交 `POST /api/analysis/jobs`
3. 拿到 `jobId` 后每 2 秒轮询 `GET /api/analysis/jobs/<job_id>`
4. 状态变为 `done` 后请求 `GET /api/analysis/jobs/<job_id>/result`
5. 渲染：
  - KPI（汇总指标）
  - 时序图（`timeseries`）
  - CSV 下载区（`downloads`）
6. 用户可导出当前结果为 JSON，或下载四类 CSV

---

## 6. 前后端接口对接明细（前端调用）

## 6.1 视频分析主接口

- `POST /api/analysis/jobs`
  - 请求参数（`FormData`）：
    - `left_video`、`right_video`
    - `fps`（默认 60）
    - `profile_json`
    - `light_mode`
    - `stereo_params_matlab_json`（可选）
- `GET /api/analysis/jobs/<job_id>`
  - 用于轮询状态：`status/stage/progress/message/error/error_code`
- `GET /api/analysis/jobs/<job_id>/result`
  - 用于结果渲染：`summaryMetrics/derivedStats/qualityFlags/timeseries/downloads/universal2`
- `GET /api/analysis/jobs/<job_id>/artifacts/<filename>`
  - 前端通过下载链接访问，不直接解析 CSV 内容

## 6.2 其它前端请求（非视频分析主链）

- `app-flow.js` 中存在：
  - `/api/custom-footworks`（增删改查）
  - `/api/profile`
  - `/api/app/exit`

---

## 7. 图表系统（视频分析面板）

图表由 `analysis-dashboard.js` 使用原生 `canvas` 绘制（非 ECharts/Chart.js）。

当前主要图表：

1. 重心速度
2. 重心加速度
3. 转向速度
4. 左右离地高度
5. 左右膝关节角度
6. 左右踝关节角度

渲染机制：

- `renderCharts()` 读取 `result.timeseries`
- `ensureChartLayout()` 动态创建图表容器
- `drawLineChart()` 执行折线绘制
- 点击图表可弹窗放大查看

---

## 8. 视频分析数据来源

## 8.1 先说结论（前端到底在用什么数据）

- 你在分析面板看到的图和 KPI，**不是前端自己算的**。
- 前端只做两件事：
  1. 去后端拿 `GET /api/analysis/jobs/<job_id>/result` 返回的 JSON
  2. 把这个 JSON 画成图、显示成指标
- CSV 是后端生成并保存在磁盘上的，前端主要用于“下载”。

## 8.2 CSV 文件清单（名称 + 位置）

后端产出并可下载的四份 CSV：

- `frame_metrics.csv`
- `session_summary.csv`
- `step_metrics.csv`
- `unit_metrics.csv`

物理路径：`web_1/jobs/<job_id>/kinematics/`

## 8.3 这些 CSV 是在哪生成的（具体文件）

- 生成阶段：后端 `kinematics` 阶段
- 直接生成逻辑：
  - `web_1/backend/analysis/kinematics_service.py`
  - `web_1/backend/analysis/universal2_compat.py` 里的 `write_legacy_csv_bundle(...)`
- 生成结果（落盘）：
  - `frame_metrics.csv`
  - `session_summary.csv`
  - `step_metrics.csv`
  - `unit_metrics.csv`
- 落盘路径：`web_1/jobs/<job_id>/kinematics/`

## 8.4 前端实际怎么拿到图表数据

关键点：前端**不直接读取 CSV 文件内容**。  
前端图表和 KPI 用的是后端把 CSV 整理好后返回的 JSON。

这个“整理动作”在：

- `web_1/backend/analysis/result_builder.py`

它会读取上面的 CSV，然后打包成前端需要的字段：

- 图表数据：`timeseries`
- KPI 数据：`summaryMetrics` + `derivedStats` + `qualityFlags`
- 下载链接：`downloads.frame_metrics_csv` 等

也就是说，前端链路是：

`CSV(后端落盘) -> result_builder.py 聚合 -> /result JSON -> analysis-dashboard.js 渲染`

## 8.5 图表字段与来源映射（你在前端看到的曲线）

`timeseries` 常用字段：

- `time_s`
- `com_speed_mps`
- `com_acceleration_mps2`
- `turning_speed_deg_s`
- `left_clearance_m` / `right_clearance_m`
- `left_knee_angle_deg` / `right_knee_angle_deg`
- `left_ankle_angle_deg` / `right_ankle_angle_deg`

这些字段最终由后端从 `frame_metrics.csv` 提炼后返回。

## 8.6 四份 CSV 各自是干什么的（口语版）

- `frame_metrics.csv`：逐帧数据，主要给图表用（速度、加速度、角度这些都在这）
- `session_summary.csv`：整段视频的汇总结果，主要给总览指标用
- `step_metrics.csv`：按步态/状态拆分的统计，偏分析导出用途
- `unit_metrics.csv`：更细粒度的单元事件统计，偏分析导出用途

## 8.7 最终保存状态（前端会不会改这些文件）

- 前端不会改 CSV，只负责下载链接展示。
- CSV 文件由后端写入任务目录后保留：
  - `web_1/jobs/<job_id>/kinematics/*.csv`
- 前端每次刷新展示，依赖的是后端接口返回的数据，不是浏览器本地缓存的 CSV。

---

## 9. 前端状态管理边界

## 9.1 浏览器本地状态

- 用户基础信息和模式选择保存在 `localStorage/sessionStorage`
- 分析运行态（`currentJobId`、轮询计时器、当前结果对象）主要是页面内存状态

## 9.2 后端持久化状态

- 任务状态：`jobs/<job_id>/meta.json`
- 分析日志：`jobs/<job_id>/logs/pipeline.log`
- 聚合结果：`jobs/<job_id>/report/report_payload.json`
- 历史结果索引：`data/analysis_results/items/res_*.json`

结论：刷新页面后，分析结果可通过后端接口恢复，不依赖前端内存。

---

