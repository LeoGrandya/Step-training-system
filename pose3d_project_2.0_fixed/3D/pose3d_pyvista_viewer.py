# -*- coding: utf-8 -*-
"""
PyVista 3D pose viewer
功能：
1. 读取 pose3d_abs_zup_ground0.csv（已做 Z 轴向上 + 地面对齐）
2. 显示人体关节点 + 骨架连线
3. 鼠标旋转 / 缩放 / 平移
4. 默认自动播放
5. 只播放一遍，到最后自动关闭窗口并结束程序
6. 显示 body_com / 足部轨迹
7. 可选 3x3 地面九宫格

安装：
pip install pyvista pandas numpy
"""

from pathlib import Path
import time

import numpy as np
import pandas as pd
import pyvista as pv

pv.global_theme.allow_empty_mesh = True

# =========================================================
# 1. User config
# =========================================================

CSV_PATH = "output\session_001\pair_008\pose3d_abs_zup_ground0.csv"

# 原始数据帧率
FPS = 60.0

# 启动后默认自动播放
AUTO_PLAY = True

# 是否循环播放
# False：只播放一遍
LOOP_PLAY = False

# 播放完成后是否自动关闭窗口并结束程序
AUTO_CLOSE_ON_FINISH = True

# None = 按 FPS 播放
# 如果想慢一点，比如 20fps，就改成 20.0
PLAYBACK_FPS = None

SHOW_NINE_GRID = True
GRID_CELL_SIZE = 0.9
GRID_TOTAL_SIZE = 2.7
GRID_CENTER_XY = None
GROUND_Z = None
SHOW_GRID_LABELS = True
SHOW_JOINT_LABELS = False
TRAIL_LENGTH = 120

JOINT_POINT_SIZE = 16
COM_POINT_SIZE = 24
BONE_LINE_WIDTH = 6
FOOT_TRAIL_WIDTH = 4
COM_TRAIL_WIDTH = 5

WINDOW_SIZE = (1600, 950)
BACKGROUND_COLOR = "white"
INTERPOLATE_MISSING = True
ONLY_SHOW_MAIN_JOINTS = True
WINDOW_TITLE = "PyVista 3D Pose Viewer"


# =========================================================
# 2. Joint aliases
# =========================================================

JOINT_ALIASES = {
    "nose": ["nose"],
    "left_eye": ["left_eye", "l_eye"],
    "right_eye": ["right_eye", "r_eye"],
    "left_ear": ["left_ear", "l_ear"],
    "right_ear": ["right_ear", "r_ear"],

    "left_shoulder": ["left_shoulder", "l_shoulder", "shoulder_left"],
    "right_shoulder": ["right_shoulder", "r_shoulder", "shoulder_right"],
    "left_elbow": ["left_elbow", "l_elbow", "elbow_left"],
    "right_elbow": ["right_elbow", "r_elbow", "elbow_right"],
    "left_wrist": ["left_wrist", "l_wrist", "wrist_left"],
    "right_wrist": ["right_wrist", "r_wrist", "wrist_right"],

    "left_hip": ["left_hip", "l_hip", "hip_left"],
    "right_hip": ["right_hip", "r_hip", "hip_right"],
    "left_knee": ["left_knee", "l_knee", "knee_left"],
    "right_knee": ["right_knee", "r_knee", "knee_right"],
    "left_ankle": ["left_ankle", "l_ankle", "ankle_left"],
    "right_ankle": ["right_ankle", "r_ankle", "ankle_right"],

    "left_heel": ["left_heel", "l_heel", "heel_left"],
    "right_heel": ["right_heel", "r_heel", "heel_right"],
    "left_foot_index": ["left_foot_index", "l_foot_index", "left_toe", "l_toe", "foot_index_left"],
    "right_foot_index": ["right_foot_index", "r_foot_index", "right_toe", "r_toe", "foot_index_right"],

    "body_com": ["body_com", "com", "center_of_mass", "body_center", "mass_center"],
    "pelvis": ["pelvis", "root", "mid_hip", "hip_center"],
}


SKELETON_EDGES = [
    ("nose", "left_shoulder"),
    ("nose", "right_shoulder"),
    ("left_shoulder", "right_shoulder"),

    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),

    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),

    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),

    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("left_ankle", "left_heel"),
    ("left_ankle", "left_foot_index"),
    ("left_heel", "left_foot_index"),

    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("right_ankle", "right_heel"),
    ("right_ankle", "right_foot_index"),
    ("right_heel", "right_foot_index"),
]

MAIN_JOINTS = sorted(set([j for e in SKELETON_EDGES for j in e] + ["body_com", "pelvis"]))


# =========================================================
# 3. Helper functions
# =========================================================

def normalize_name(name: str) -> str:
    if pd.isna(name):
        return ""
    s = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    for std_name, aliases in JOINT_ALIASES.items():
        if s == std_name or s in aliases:
            return std_name
    return s


def find_first_column(df: pd.DataFrame, candidates):
    lower_map = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def valid_point(pt):
    if pt is None:
        return False
    pt = np.asarray(pt, dtype=float)
    return np.isfinite(pt).all()


def make_points_polydata(points):
    if points is None or len(points) == 0:
        return pv.PolyData(np.empty((0, 3)))
    return pv.PolyData(np.array(points, dtype=float))


def make_lines_polydata(points_map, edges):
    used_points = {}
    pts = []
    lines = []

    def get_idx(joint):
        if joint not in used_points:
            used_points[joint] = len(pts)
            pts.append(points_map[joint])
        return used_points[joint]

    for a, b in edges:
        if a in points_map and b in points_map:
            if valid_point(points_map[a]) and valid_point(points_map[b]):
                ia = get_idx(a)
                ib = get_idx(b)
                lines.extend([2, ia, ib])

    if len(pts) == 0 or len(lines) == 0:
        return pv.PolyData(np.empty((0, 3)))

    poly = pv.PolyData(np.array(pts, dtype=float))
    poly.lines = np.array(lines, dtype=np.int64)
    return poly


def make_trail_polydata(points):
    if points is None or len(points) < 2:
        return pv.PolyData(np.empty((0, 3)))
    points = np.array(points, dtype=float)
    poly = pv.PolyData(points)
    lines = []
    for i in range(len(points) - 1):
        lines.extend([2, i, i + 1])
    poly.lines = np.array(lines, dtype=np.int64)
    return poly


def estimate_ground_z(joint_arrays):
    foot_candidates = [
        "left_heel", "right_heel",
        "left_ankle", "right_ankle",
        "left_foot_index", "right_foot_index"
    ]
    z_values = []
    for j in foot_candidates:
        if j in joint_arrays:
            z = joint_arrays[j][:, 2]
            z = z[np.isfinite(z)]
            if len(z) > 0:
                z_values.extend(z.tolist())
    if len(z_values) == 0:
        return 0.0
    return float(np.percentile(np.array(z_values), 5))


def estimate_grid_center_xy(joint_arrays, num_frames=30):
    if "body_com" in joint_arrays:
        arr = joint_arrays["body_com"][:num_frames, :2]
        arr = arr[np.isfinite(arr).all(axis=1)]
        if len(arr) > 0:
            return tuple(np.mean(arr, axis=0))

    if "left_hip" in joint_arrays and "right_hip" in joint_arrays:
        lh = joint_arrays["left_hip"][:num_frames]
        rh = joint_arrays["right_hip"][:num_frames]
        mid = (lh[:, :2] + rh[:, :2]) / 2.0
        mid = mid[np.isfinite(mid).all(axis=1)]
        if len(mid) > 0:
            return tuple(np.mean(mid, axis=0))

    return (0.0, 0.0)


def build_nine_grid(center_xy, ground_z, cell_size=0.9, total_size=2.7):
    """
    修正后的九宫格编号：
    第一行：1 2 3
    第二行：4 5 6
    第三行：7 8 9
    """
    cx, cy = center_xy
    half = total_size / 2.0

    xs = [cx - half, cx - half + cell_size, cx - half + 2 * cell_size, cx + half]
    ys = [cy - half, cy - half + cell_size, cy - half + 2 * cell_size, cy + half]

    points = []
    lines = []

    def add_segment(p1, p2):
        i1 = len(points)
        points.append(p1)
        i2 = len(points)
        points.append(p2)
        lines.extend([2, i1, i2])

    for x in xs:
        add_segment([x, ys[0], ground_z], [x, ys[-1], ground_z])

    for y in ys:
        add_segment([xs[0], y, ground_z], [xs[-1], y, ground_z])

    poly = pv.PolyData(np.array(points, dtype=float))
    poly.lines = np.array(lines, dtype=np.int64)

    centers = []
    labels = []
    num = 1

    # 这里把列方向翻转，修正 1/3、4/6、7/9 左右反了的问题
    for row in range(3):
        for col in range(3):
            x0 = xs[2 - col]
            x1 = xs[3 - col]
            y0 = ys[2 - row]
            y1 = ys[3 - row]
            centers.append([(x0 + x1) / 2, (y0 + y1) / 2, ground_z + 0.01])
            labels.append(str(num))
            num += 1

    return poly, np.array(centers, dtype=float), labels


def locate_nine_grid_cell(x, y, center_xy, cell_size=0.9, total_size=2.7):
    """
    与 build_nine_grid 保持一致：
    第一行：1 2 3
    第二行：4 5 6
    第三行：7 8 9
    """
    cx, cy = center_xy
    half = total_size / 2.0
    x_min = cx - half
    y_min = cy - half

    if not (x_min <= x <= x_min + total_size and y_min <= y <= y_min + total_size):
        return None

    col = int((x - x_min) // cell_size)
    row_from_bottom = int((y - y_min) // cell_size)

    if col < 0 or col > 2 or row_from_bottom < 0 or row_from_bottom > 2:
        return None

    # 水平方向翻转，和显示标签一致
    col = 2 - col
    row_from_top = 2 - row_from_bottom
    return row_from_top * 3 + col + 1


def get_preferred_com(frame_points):
    if "body_com" in frame_points and valid_point(frame_points["body_com"]):
        return frame_points["body_com"]

    if "pelvis" in frame_points and valid_point(frame_points["pelvis"]):
        return frame_points["pelvis"]

    if ("left_hip" in frame_points and "right_hip" in frame_points
            and valid_point(frame_points["left_hip"])
            and valid_point(frame_points["right_hip"])):
        return (frame_points["left_hip"] + frame_points["right_hip"]) / 2.0

    return None


# =========================================================
# 4. Data loading
# =========================================================

def load_pose3d_csv(csv_path):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path.resolve()}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    frame_col = find_first_column(df, ["frame_id", "frame", "frame_idx", "index"])
    joint_col = find_first_column(df, ["joint_name", "joint", "name", "landmark"])
    x_col = find_first_column(df, ["x", "X"])
    y_col = find_first_column(df, ["y", "Y"])
    z_col = find_first_column(df, ["z", "Z"])
    conf_col = find_first_column(df, ["confidence", "conf", "score", "visibility"])

    missing = [k for k, v in {
        "frame": frame_col,
        "joint": joint_col,
        "x": x_col,
        "y": y_col,
        "z": z_col,
    }.items() if v is None]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    use_cols = [frame_col, joint_col, x_col, y_col, z_col]
    if conf_col is not None:
        use_cols.append(conf_col)

    df = df[use_cols].copy()
    df.columns = ["frame", "joint", "x", "y", "z"] + (["confidence"] if conf_col is not None else [])

    df["joint"] = df["joint"].apply(normalize_name)
    df["frame"] = pd.to_numeric(df["frame"], errors="coerce")
    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df["z"] = pd.to_numeric(df["z"], errors="coerce")

    df = df.dropna(subset=["frame", "joint"])
    df["frame"] = df["frame"].astype(int)

    agg_cols = {"x": "mean", "y": "mean", "z": "mean"}
    if "confidence" in df.columns:
        agg_cols["confidence"] = "mean"
    df = df.groupby(["frame", "joint"], as_index=False).agg(agg_cols)

    frames = np.sort(df["frame"].unique())
    joints = sorted(df["joint"].unique().tolist())

    joint_arrays = {}
    frame_to_idx = {f: i for i, f in enumerate(frames)}

    for joint in joints:
        arr = np.full((len(frames), 3), np.nan, dtype=float)
        sub = df[df["joint"] == joint]
        for _, row in sub.iterrows():
            i = frame_to_idx[int(row["frame"])]
            arr[i] = [row["x"], row["y"], row["z"]]

        if INTERPOLATE_MISSING:
            for c in range(3):
                s = pd.Series(arr[:, c])
                s = s.interpolate(limit_direction="both")
                arr[:, c] = s.to_numpy()

        joint_arrays[joint] = arr

    return df, frames, joints, joint_arrays


# =========================================================
# 5. Main viewer
# =========================================================

class Pose3DViewer:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.df, self.frames, self.joints, self.joint_arrays = load_pose3d_csv(csv_path)

        self.num_frames = len(self.frames)
        self.current_idx = 0
        self.is_playing = AUTO_PLAY
        self.finished_once = False

        self.playback_fps = float(FPS if PLAYBACK_FPS is None else PLAYBACK_FPS)
        self.play_interval_ms = max(1, int(round(1000.0 / max(1.0, self.playback_fps))))

        self.available_main_joints = [j for j in MAIN_JOINTS if j in self.joint_arrays]
        self.visible_joints = self.available_main_joints if ONLY_SHOW_MAIN_JOINTS else self.joints

        self.ground_z = GROUND_Z if GROUND_Z is not None else estimate_ground_z(self.joint_arrays)
        self.grid_center_xy = GRID_CENTER_XY if GRID_CENTER_XY is not None else estimate_grid_center_xy(self.joint_arrays)

        self.plotter = pv.Plotter(
            title=WINDOW_TITLE,
            window_size=WINDOW_SIZE
        )
        self.plotter.set_background(BACKGROUND_COLOR)

        self._init_static_scene()
        self._register_events()
        self.update_scene(self.current_idx)

    def _init_static_scene(self):
        self.plotter.add_axes()
        self.plotter.show_bounds(
            grid="back",
            location="outer",
            all_edges=True,
            xtitle="X",
            ytitle="Y",
            ztitle="Z",
            font_size=12
        )

        if SHOW_NINE_GRID:
            grid_poly, grid_centers, grid_labels = build_nine_grid(
                center_xy=self.grid_center_xy,
                ground_z=self.ground_z,
                cell_size=GRID_CELL_SIZE,
                total_size=GRID_TOTAL_SIZE
            )

            self.plotter.add_mesh(
                grid_poly,
                color="black",
                line_width=2,
                render_lines_as_tubes=True,
                name="nine_grid"
            )

            plane = pv.Plane(
                center=(self.grid_center_xy[0], self.grid_center_xy[1], self.ground_z - 0.002),
                direction=(0, 0, 1),
                i_size=GRID_TOTAL_SIZE,
                j_size=GRID_TOTAL_SIZE,
                i_resolution=1,
                j_resolution=1
            )
            self.plotter.add_mesh(
                plane,
                color="lightgray",
                opacity=0.15,
                show_edges=False,
                name="ground_plane"
            )

            if SHOW_GRID_LABELS:
                self.plotter.add_point_labels(
                    grid_centers,
                    grid_labels,
                    font_size=12,
                    text_color="black",
                    point_color="white",
                    point_size=1,
                    shape=None,
                    name="grid_labels"
                )

        self.plotter.view_isometric()
        self.plotter.camera.up = (0, 0, 1)
        self.plotter.enable_trackball_style()

        self.plotter.add_text(
            "L-drag rotate  R-drag zoom  M-drag pan  Shift+L pan  "
            "Left/Right frame  Space/P play-pause  Home/End  R reset  T top  F front  S side",
            position="upper_left",
            font_size=10,
            color="black",
            name="static_help"
        )

        self.plotter.add_text(
            f"CSV: {Path(self.csv_path).name}",
            position="lower_left",
            font_size=10,
            color="black",
            name="csv_info"
        )

    def _register_events(self):
        self.plotter.add_key_event("Left", self.prev_frame)
        self.plotter.add_key_event("Right", self.next_frame)
        self.plotter.add_key_event("Home", self.first_frame)
        self.plotter.add_key_event("End", self.last_frame)

        self.plotter.add_key_event("space", self.toggle_play)
        self.plotter.add_key_event("p", self.toggle_play)
        self.plotter.add_key_event("P", self.toggle_play)

        self.plotter.add_key_event("r", self.reset_view)
        self.plotter.add_key_event("t", self.view_top)
        self.plotter.add_key_event("f", self.view_front)
        self.plotter.add_key_event("s", self.view_side)

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.update_scene(self.current_idx)

    def reset_view(self):
        self.plotter.view_isometric()
        self.plotter.camera.up = (0, 0, 1)
        self.plotter.reset_camera()
        self.plotter.render()

    def view_top(self):
        self.plotter.view_xy()
        self.plotter.camera.up = (0, 1, 0)
        self.plotter.reset_camera()
        self.plotter.render()

    def view_front(self):
        self.plotter.view_xz()
        self.plotter.camera.up = (0, 0, 1)
        self.plotter.reset_camera()
        self.plotter.render()

    def view_side(self):
        self.plotter.view_yz()
        self.plotter.camera.up = (0, 0, 1)
        self.plotter.reset_camera()
        self.plotter.render()

    def prev_frame(self):
        self.is_playing = False
        self.current_idx = max(0, self.current_idx - 1)
        self.update_scene(self.current_idx)

    def next_frame(self):
        self.is_playing = False
        self.current_idx = min(self.num_frames - 1, self.current_idx + 1)
        self.update_scene(self.current_idx)

    def first_frame(self):
        self.is_playing = False
        self.current_idx = 0
        self.update_scene(self.current_idx)

    def last_frame(self):
        self.is_playing = False
        self.current_idx = self.num_frames - 1
        self.update_scene(self.current_idx)

    def get_frame_points(self, frame_idx):
        points = {}
        for j in self.visible_joints:
            if j in self.joint_arrays:
                pt = self.joint_arrays[j][frame_idx]
                if valid_point(pt):
                    points[j] = pt.copy()

        if "body_com" in self.joint_arrays:
            pt = self.joint_arrays["body_com"][frame_idx]
            if valid_point(pt):
                points["body_com"] = pt.copy()

        if "pelvis" in self.joint_arrays:
            pt = self.joint_arrays["pelvis"][frame_idx]
            if valid_point(pt):
                points["pelvis"] = pt.copy()

        return points

    def get_trail_points(self, joint_name, current_idx, trail_length=120):
        if joint_name not in self.joint_arrays:
            return None
        start = max(0, current_idx - trail_length + 1)
        arr = self.joint_arrays[joint_name][start:current_idx + 1]
        arr = arr[np.isfinite(arr).all(axis=1)]
        return arr if len(arr) > 0 else None

    def get_com_trail_points(self, current_idx, trail_length=120):
        start = max(0, current_idx - trail_length + 1)
        trail = []
        for i in range(start, current_idx + 1):
            frame_points = self.get_frame_points(i)
            com = get_preferred_com(frame_points)
            if valid_point(com):
                trail.append(com.copy())
        return np.array(trail, dtype=float) if len(trail) > 0 else None

    def update_scene(self, frame_idx):
        frame_points = self.get_frame_points(frame_idx)

        joint_pts = []
        joint_names = []
        for j, pt in frame_points.items():
            if j != "body_com":
                joint_pts.append(pt)
                joint_names.append(j)

        self.plotter.remove_actor("joint_points", render=False)
        self.plotter.remove_actor("com_point", render=False)
        self.plotter.remove_actor("skeleton_lines", render=False)
        self.plotter.remove_actor("left_foot_trail", render=False)
        self.plotter.remove_actor("right_foot_trail", render=False)
        self.plotter.remove_actor("com_trail", render=False)
        self.plotter.remove_actor("hud_text", render=False)
        if SHOW_JOINT_LABELS:
            self.plotter.remove_actor("joint_labels", render=False)

        joint_poly = make_points_polydata(joint_pts)
        self.plotter.add_mesh(
            joint_poly,
            color="dodgerblue",
            point_size=JOINT_POINT_SIZE,
            render_points_as_spheres=True,
            name="joint_points",
            reset_camera=False
        )

        com = get_preferred_com(frame_points)
        com_poly = make_points_polydata([com]) if valid_point(com) else make_points_polydata([])
        self.plotter.add_mesh(
            com_poly,
            color="red",
            point_size=COM_POINT_SIZE,
            render_points_as_spheres=True,
            name="com_point",
            reset_camera=False
        )

        line_poly = make_lines_polydata(frame_points, SKELETON_EDGES)
        self.plotter.add_mesh(
            line_poly,
            color="black",
            line_width=BONE_LINE_WIDTH,
            render_lines_as_tubes=True,
            name="skeleton_lines",
            reset_camera=False
        )

        left_trail_joint = next((c for c in ["left_ankle", "left_heel", "left_foot_index"] if c in self.joint_arrays), None)
        if left_trail_joint:
            left_trail = self.get_trail_points(left_trail_joint, frame_idx, TRAIL_LENGTH)
            self.plotter.add_mesh(
                make_trail_polydata(left_trail),
                color="green",
                line_width=FOOT_TRAIL_WIDTH,
                render_lines_as_tubes=True,
                name="left_foot_trail",
                reset_camera=False
            )

        right_trail_joint = next((c for c in ["right_ankle", "right_heel", "right_foot_index"] if c in self.joint_arrays), None)
        if right_trail_joint:
            right_trail = self.get_trail_points(right_trail_joint, frame_idx, TRAIL_LENGTH)
            self.plotter.add_mesh(
                make_trail_polydata(right_trail),
                color="orange",
                line_width=FOOT_TRAIL_WIDTH,
                render_lines_as_tubes=True,
                name="right_foot_trail",
                reset_camera=False
            )

        com_trail = self.get_com_trail_points(frame_idx, TRAIL_LENGTH)
        self.plotter.add_mesh(
            make_trail_polydata(com_trail),
            color="red",
            line_width=COM_TRAIL_WIDTH,
            render_lines_as_tubes=True,
            name="com_trail",
            reset_camera=False
        )

        if SHOW_JOINT_LABELS and len(joint_pts) > 0:
            self.plotter.add_point_labels(
                np.array(joint_pts),
                joint_names,
                font_size=10,
                text_color="black",
                point_color="white",
                point_size=1,
                shape=None,
                always_visible=True,
                name="joint_labels"
            )

        frame_no = int(self.frames[frame_idx])
        cell_info = ""
        if valid_point(com):
            cell_id = locate_nine_grid_cell(
                com[0], com[1],
                center_xy=self.grid_center_xy,
                cell_size=GRID_CELL_SIZE,
                total_size=GRID_TOTAL_SIZE
            )
            cell_info = f"  COM cell: {cell_id}" if cell_id is not None else "  COM cell: outside"

        play_state = "PLAY" if self.is_playing else "PAUSE"
        hud = (
            f"Frame: {frame_idx + 1}/{self.num_frames} "
            f"(frame_id={frame_no}) {play_state} "
            f"fps={self.playback_fps:.2f}{cell_info}"
        )
        self.plotter.add_text(
            hud,
            position="upper_right",
            font_size=11,
            color="black",
            name="hud_text"
        )

        self.plotter.render()

    def _advance_one_frame(self):
        if self.current_idx < self.num_frames - 1:
            self.current_idx += 1
            self.update_scene(self.current_idx)
            return

        # 已到最后一帧
        if LOOP_PLAY:
            self.current_idx = 0
            self.update_scene(self.current_idx)
            return

        self.is_playing = False
        self.finished_once = True
        self.update_scene(self.current_idx)

    def start(self):
        self.plotter.show(auto_close=False, interactive_update=True)

        print(f"[INFO] Auto play started: interval={self.play_interval_ms} ms")
        print(f"[INFO] playback_fps = {self.playback_fps:.2f}")
        print(f"[INFO] loop_play = {LOOP_PLAY}")
        print(f"[INFO] auto_close_on_finish = {AUTO_CLOSE_ON_FINISH}")

        next_tick = time.perf_counter()

        while True:
            try:
                if getattr(self.plotter, "_closed", False):
                    break

                if getattr(self.plotter, "ren_win", None) is None:
                    break

                now = time.perf_counter()

                if self.is_playing and now >= next_tick:
                    self._advance_one_frame()
                    next_tick = now + (self.play_interval_ms / 1000.0)

                self.plotter.update()

                if self.finished_once and AUTO_CLOSE_ON_FINISH:
                    time.sleep(0.2)
                    break

                time.sleep(0.001)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[WARN] Viewer loop stopped: {e}")
                break

        try:
            self.plotter.close()
        except Exception:
            pass


def main():
    print("Starting PyVista 3D pose viewer...")
    print(f"Reading file: {CSV_PATH}")
    viewer = Pose3DViewer(CSV_PATH)
    viewer.start()


if __name__ == "__main__":
    main()