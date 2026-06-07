# pose3d_project（MediaPipe 专用增强版）

本版只保留 **MediaPipe Pose Landmarker**，并新增：
- **left_heel / right_heel**：直接使用 MediaPipe 官方 33 点里的脚跟点。
- **left_foot_direction / right_foot_direction**：在 `foot_index` 基础上沿脚跟→脚尖方向外推的两个辅助点，用来显示脚掌/脚尖方向。
- **body_com**：基于 3D 髋部、肩部、足部位置计算的近似重心点。

Google 官方 Pose Landmarker 文档说明其会输出 **33 个 3D 身体关键点**，其中明确包含 `left heel`、`right heel`、`left foot index`、`right foot index`。citeturn966347search0turn966347search1

## 当前输出结构
- `pose2d_all.csv`：默认导出 **mediapipe35**（33 点 + 2 个脚方向点）
- `pose3d_abs.csv`：导出 **mediapipe36**（35 点 + body_com）
- `pose3d_relative.csv`：相对 3D 坐标，默认以 `body_com` 为根
- `paraview/`：可直接在 ParaView 中显示人体、脚方向点、重心点、坐标轴和轨迹

## 运行方式
在项目根目录执行：

```bash
python -m pose3d_pkg.cli.run_pipeline
```

## 输入要求
把视频与统一的相机参数放在：

```text
data/session_001/
  left1.mp4
  right1.mp4
  left2.mp4
  right2.mp4
  stereo_params.json
```

## 模型文件
需要准备：

```text
models/pose_landmarker_full.task
```

## 说明
- `body_com` 是工程近似重心点，适合步法移动范围、轨迹与重心转移趋势分析，不等同于严格生物力学质心。
- ParaView 中的 `root_trajectory.csv` 默认输出 `body_com` 轨迹。
