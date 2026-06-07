# 视频同步内核（video_sync/lib）

**Web 分析管线**（`web_1`）仅依赖本目录下的 **`lib/sync.py`**（`run_sync`）。  
Streamlit 页面、CLI 抽帧、`sync_two_videos.py` 等已迁至 **[`_archive/video_sync_tools/`](../_archive/README.md)**。

## 运行时模块

- `lib/sync.py` — 音轨互相关同步 + 对齐双路抽帧（`extract_frames`）
- `tests/test_imwrite_path.py` — 中文路径写图单元测试

## 归档工具（非运行时）

见 [`_archive/README.md`](../_archive/README.md)：

- Streamlit：`_archive/video_sync_tools/streamlit_sync_extract_app.py`
- CLI：`scripts/extract_frames.py`、`sync_two_videos.py`（在归档目录内）
- 启动：`_archive/video_sync_tools/start_streamlit.bat`

## 环境要求

- Python 3.9+
- [FFmpeg](https://ffmpeg.org/download.html)（需可执行 `ffmpeg`、`ffprobe` 并加入 `PATH`）

## 安装

### 1) 安装 FFmpeg

安装完成后请先验证：

```bash
ffmpeg -version
ffprobe -version
```

Windows 推荐安装方式：

1. `winget install Gyan.FFmpeg`
2. 或 `choco install ffmpeg`
3. 或手动下载并将 FFmpeg `bin` 目录加入系统 `PATH`

### 2) 安装 Python 依赖

```bash
cd video_sync
pip install -r requirements.txt
```

### 3) 安装为 Python 包（可分发 wheel）

在 **仓库根目录** `lookfeet/`（与 `pyproject.toml` 同级）执行：

```bash
# 可编辑安装（开发）
pip install -e .

# 构建 wheel / sdist 到 dist/
pip install build
python -m build
```

安装后可在任意目录使用入口命令（需已配置 FFmpeg）：

- `video-sync` — 等价于 `python -m video_sync.sync_two_videos`
- `video-sync-frames` — 抽帧 CLI
- `video-sync-web` — 启动 Streamlit 页面

也可：`pip install dist/lookfeet_video_sync-0.1.0-py3-none-any.whl`（版本号以实际文件名为准）。

## 快速开始

### A. 启动 Web 页面（推荐）

**一键点击启动（Windows）**

- 双击 `start_web.bat` 即可启动 Web 页面
- 或命令行执行：

```bash
cd video_sync
python scripts/launch_web.py
```

**标准命令方式**

```bash
cd video_sync
streamlit run streamlit_sync_extract_app.py
```

页面流程：

1. 在“视频同步”区选择左右视频并点击开始同步
2. 同步完成后在“同步抽帧”区直接使用同步结果或重新选择视频
3. 点击开始抽帧，输出成对图片

同步模式说明：

1. **单个**：手动选择左右两个视频，处理 1 组
2. **按文件名匹配**：选择左右目录，按文件名（忽略扩展名与大小写）匹配，例如 `0001.mp4` 与 `0001.mov`
3. **按顺序匹配**：选择左右目录，按各自目录内排序后的顺序一一配对，配对数取两侧较少数量
4. 批量模式执行后会在页面中汇总成功与失败项

默认输出根目录：

- 若仓库内存在上级目录下的 `web_output` 文件夹，则沿用该路径（与旧版一致）
- 否则默认为 **当前工作目录** 下的 `video_sync_web_output/`

对齐视频：`…/synced_videos/`；抽帧：`…/extracted_frames/run_YYYYMMDD_HHMMSS/left|right/`

### B. 仅用同步脚本（CLI）

指定输出文件：

```bash
python sync_two_videos.py A.mp4 B.mp4 -o D:\out\a.mp4 E:\out\b.mp4
```

指定输出目录（自动生成 `*_aligned.mp4`）：

```bash
python sync_two_videos.py A.mp4 B.mp4 --out-dir-a D:\out1 --out-dir-b D:\out2
```

自动结果不理想时，可手动微调 B 路偏移：

```bash
python sync_two_videos.py A.mp4 B.mp4 -o oa.mp4 ob.mp4 --manual-offset 0.05
```

### C. 仅用抽帧脚本（CLI）

```bash
python scripts/extract_frames.py --left A_aligned.mp4 --right B_aligned.mp4 --output D:\frames --interval 30 --start 0 --max 0
```

说明：

- `--max 0` 代表不限制（建议在调用端转换为 `None`）
- 输出结构固定为：
  - `D:\frames\left\left_000000.jpg`
  - `D:\frames\right\right_000000.jpg`

## 参数说明

### 同步（`sync_two_videos.py`）

- `--manual-offset`：在自动对齐结果上，额外给 B 视频增加开头裁切秒数
- `--max-audio-seconds`：参与互相关计算的音频长度上限（秒）
- `--crf`：x264 恒定质量参数
  - 值越小：画质更高、文件更大
  - 值越大：画质更低、文件更小
  - 常用范围：`18-28`，默认 `20`
- `--no-progress`：CLI 下关闭 tqdm 进度条

### 抽帧（`scripts/extract_frames.py`）

- `--interval`：每隔多少帧抽一帧
- `--start`：从哪一帧开始抽
- `--max`：最多抽多少对，默认全部

## 工作原理

### 视频同步

1. 从两路视频导出单声道 WAV
2. 对音频波形做互相关，估计相对延迟
3. 根据延迟裁掉两路开头并按重叠时长重编码输出

### 抽帧

1. 同步读取左右视频帧
2. 在相同帧索引按间隔采样
3. 保存为一一对应的左右图片对

## 常见问题

- **同步失败，提示 ffmpeg/ffprobe 不存在**
  - 检查 FFmpeg 是否安装并加入 `PATH`
- **自动对齐不准**
  - 提高 `--max-audio-seconds`，或用 `--manual-offset` 微调
  - 确保两路有足够重叠音频（环境声、人声、拍板声）
- **抽帧数量偏少**
  - 检查 `--interval` / `--start` / `--max` 参数
- **界面显示抽帧完成，但 `left`/`right` 文件夹为空**
  - 旧版本在 Windows 中文路径下 `cv2.imwrite` 可能静默失败却仍计数；请使用当前版本（`imencode` + `Path.write_bytes` 写盘，并校验文件）
  - 若仍失败：检查目录写入权限、杀毒软件拦截；或将输出根目录改为纯英文路径（如 `D:\video_sync_out`）
  - 查看运行 Streamlit / CLI 的终端是否出现「无法写入左图/右图」或 `RuntimeError: 抽帧写盘失败`

## 项目结构

```text
video_sync/
  sync_two_videos.py
  streamlit_sync_extract_app.py
  start_web.bat
  scripts/
    extract_frames.py
    launch_web.py
  docs/
    generated/        # 约定：自动生成的说明文档放这里
  lib/
    sync.py           # 同步 + 抽帧（单文件）
  tests/
    test_imwrite_path.py  # 中文路径写图单元测试
```

### 运行写图测试

```bash
cd video_sync
python -m unittest tests.test_imwrite_path
```


