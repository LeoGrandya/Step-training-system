from pathlib import Path
import pandas as pd

JOINT_ALIASES = {
    "body_com": ["body_com", "com", "center_of_mass", "body_center", "mass_center"],
    "pelvis": ["pelvis", "root", "mid_hip", "hip_center"],
    "left_hip": ["left_hip", "l_hip", "hip_left"],
    "right_hip": ["right_hip", "r_hip", "hip_right"],
    "left_knee": ["left_knee", "l_knee", "knee_left"],
    "right_knee": ["right_knee", "r_knee", "knee_right"],
    "left_ankle": ["left_ankle", "l_ankle", "ankle_left"],
    "right_ankle": ["right_ankle", "r_ankle", "ankle_right"],
    "left_heel": ["left_heel", "l_heel", "heel_left"],
    "right_heel": ["right_heel", "r_heel", "heel_right"],
    "left_foot_index": ["left_foot_index", "l_foot_index", "left_toe", "l_toe"],
    "right_foot_index": ["right_foot_index", "r_foot_index", "right_toe", "r_toe"],
    "left_shoulder": ["left_shoulder", "l_shoulder", "shoulder_left"],
    "right_shoulder": ["right_shoulder", "r_shoulder", "shoulder_right"],
}


def normalize_joint_name(name: str) -> str:
    if pd.isna(name):
        return ""
    s = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    for std_name, aliases in JOINT_ALIASES.items():
        if s == std_name or s in aliases:
            return std_name
    return s


def find_first_column(df: pd.DataFrame, candidates):
    lower_map = {str(c).lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def _wide_to_long(df: pd.DataFrame, frame_col: str) -> pd.DataFrame:
    columns = {str(col): col for col in df.columns}
    joints = []
    for name in columns:
        if not name.endswith("_x"):
            continue
        joint = name[:-2]
        if f"{joint}_y" in columns and f"{joint}_z" in columns:
            joints.append(joint)
    if not joints:
        raise ValueError("输入 CSV 缺少必要列: ['joint', 'x', 'y', 'z']")

    parts = []
    for joint in sorted(joints):
        part = df[[frame_col, columns[f"{joint}_x"], columns[f"{joint}_y"], columns[f"{joint}_z"]]].copy()
        part.columns = ["frame_id", "x", "y", "z"]
        part["joint_name"] = normalize_joint_name(joint)
        parts.append(part)
    return pd.concat(parts, ignore_index=True)[["frame_id", "joint_name", "x", "y", "z"]]


def load_pose3d_long(csv_path, fps: float = 60.0) -> pd.DataFrame:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    frame_col = find_first_column(df, ["frame_id", "frame", "frame_idx", "index"])
    joint_col = find_first_column(df, ["joint_name", "joint", "name", "landmark"])
    x_col = find_first_column(df, ["x", "X"])
    y_col = find_first_column(df, ["y", "Y"])
    z_col = find_first_column(df, ["z", "Z"])

    if frame_col is not None and (joint_col is None or x_col is None or y_col is None or z_col is None):
        df = _wide_to_long(df, frame_col)
        frame_col = "frame_id"
        joint_col = "joint_name"
        x_col = "x"
        y_col = "y"
        z_col = "z"

    missing = [k for k, v in {
        "frame": frame_col,
        "joint": joint_col,
        "x": x_col,
        "y": y_col,
        "z": z_col,
    }.items() if v is None]
    if missing:
        raise ValueError(f"输入 CSV 缺少必要列: {missing}")

    df = df[[frame_col, joint_col, x_col, y_col, z_col]].copy()
    df.columns = ["frame_id", "joint_name", "x", "y", "z"]

    df["frame_id"] = pd.to_numeric(df["frame_id"], errors="coerce")
    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df["z"] = pd.to_numeric(df["z"], errors="coerce")
    df["joint_name"] = df["joint_name"].apply(normalize_joint_name)

    df = df.dropna(subset=["frame_id", "joint_name"])
    df["frame_id"] = df["frame_id"].astype(int)

    df = (
        df.groupby(["frame_id", "joint_name"], as_index=False)
        .agg({"x": "mean", "y": "mean", "z": "mean"})
        .sort_values(["frame_id", "joint_name"])
        .reset_index(drop=True)
    )

    source_frames = sorted(df["frame_id"].dropna().astype(int).unique().tolist())
    frame_map = {source_frame: idx for idx, source_frame in enumerate(source_frames)}
    df["source_frame_id"] = df["frame_id"].astype(int)
    df["frame_id"] = df["source_frame_id"].map(frame_map).astype(int)
    df["time_s"] = df["frame_id"] / float(fps)
    return df
