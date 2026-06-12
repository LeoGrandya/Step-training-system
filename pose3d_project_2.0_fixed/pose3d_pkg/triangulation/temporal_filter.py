from pathlib import Path

import numpy as np
import pandas as pd


def _validate_window_size(window_size: int) -> int:
    window_size = int(window_size)
    if window_size < 1:
        raise ValueError("window_size 必须 >= 1")
    if window_size % 2 == 0:
        raise ValueError("window_size 必须是奇数，例如 3 / 5 / 7")
    return window_size


def _smooth_series(series: pd.Series, method: str, window_size: int) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").astype(float)

    if method == "moving_average":
        return s.rolling(window=window_size, center=True, min_periods=1).mean()
    if method == "ema":
        alpha = 2.0 / (window_size + 1.0)
        return s.ewm(alpha=alpha, adjust=False, min_periods=1).mean()
    if method == "median_then_mean":
        s1 = s.rolling(window=window_size, center=True, min_periods=1).median()
        s2 = s1.rolling(window=window_size, center=True, min_periods=1).mean()
        return s2
    raise ValueError(f"不支持的时序滤波方法: {method}")


def _build_joint_name_to_id(df_abs: pd.DataFrame):
    joint_df = df_abs[["joint_id", "joint_name"]].drop_duplicates().copy()
    joint_df["joint_id"] = pd.to_numeric(joint_df["joint_id"], errors="coerce")
    joint_df = joint_df.dropna(subset=["joint_id"]).sort_values("joint_id")
    return {str(row["joint_name"]): int(row["joint_id"]) for _, row in joint_df.iterrows()}


def _resolve_root_joint_id(joint_name_to_id, root_joint_id=None, root_joint_name=None):
    if root_joint_name is not None and str(root_joint_name).strip() != "":
        return joint_name_to_id.get(str(root_joint_name).strip())
    if root_joint_id is not None:
        try:
            return int(root_joint_id)
        except Exception:
            return None
    return None


def smooth_pose3d_abs_dataframe(df_abs: pd.DataFrame, method: str = "median_then_mean", window_size: int = 5) -> pd.DataFrame:
    window_size = _validate_window_size(window_size)
    method = str(method).lower()

    df = df_abs.copy()
    for col in ["x", "y", "z"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["valid"] = pd.to_numeric(df["valid"], errors="coerce").fillna(0).astype(int)

    result_parts = []
    for joint_id, grp in df.groupby("joint_id", sort=True):
        g = grp.sort_values("frame_id").copy()
        valid_mask = g["valid"] == 1
        x_smoothed = _smooth_series(g["x"].where(valid_mask), method, window_size)
        y_smoothed = _smooth_series(g["y"].where(valid_mask), method, window_size)
        z_smoothed = _smooth_series(g["z"].where(valid_mask), method, window_size)
        g.loc[valid_mask, "x"] = x_smoothed[valid_mask]
        g.loc[valid_mask, "y"] = y_smoothed[valid_mask]
        g.loc[valid_mask, "z"] = z_smoothed[valid_mask]
        g.loc[~valid_mask, ["x", "y", "z"]] = np.nan
        result_parts.append(g)

    out = pd.concat(result_parts, ignore_index=True)
    out = out.sort_values(["frame_id", "joint_id"]).reset_index(drop=True)
    return out


def compute_frame_root_from_abs_frame(df_frame: pd.DataFrame, root_mode: str = "pelvis_midpoint", root_joint_id: int | None = None, root_joint_name: str | None = None):
    valid_df = df_frame[(df_frame["valid"] == 1)].copy()
    joint_name_to_id = _build_joint_name_to_id(valid_df)

    if root_mode == "pelvis_midpoint":
        left_id = joint_name_to_id.get("left_hip")
        right_id = joint_name_to_id.get("right_hip")
        left = valid_df[valid_df["joint_id"] == left_id] if left_id is not None else pd.DataFrame()
        right = valid_df[valid_df["joint_id"] == right_id] if right_id is not None else pd.DataFrame()
        if len(left) > 0 and len(right) > 0:
            left_xyz = left[["x", "y", "z"]].iloc[0].to_numpy(dtype=float)
            right_xyz = right[["x", "y", "z"]].iloc[0].to_numpy(dtype=float)
            return (left_xyz + right_xyz) / 2.0

    resolved_root_joint_id = _resolve_root_joint_id(joint_name_to_id, root_joint_id=root_joint_id, root_joint_name=root_joint_name)
    if resolved_root_joint_id is not None:
        target = valid_df[valid_df["joint_id"] == int(resolved_root_joint_id)]
        if len(target) > 0:
            return target[["x", "y", "z"]].iloc[0].to_numpy(dtype=float)

    if len(valid_df) > 0:
        return valid_df.sort_values("joint_id")[["x", "y", "z"]].iloc[0].to_numpy(dtype=float)
    return None


def build_relative_pose3d_dataframe(df_abs: pd.DataFrame, root_mode: str = "pelvis_midpoint", root_joint_id: int | None = None, root_joint_name: str | None = None) -> pd.DataFrame:
    rows = []
    joint_name_to_id = _build_joint_name_to_id(df_abs)
    resolved_root_joint_id = _resolve_root_joint_id(joint_name_to_id, root_joint_id=root_joint_id, root_joint_name=root_joint_name)

    for frame_id, grp in df_abs.groupby("frame_id", sort=True):
        g = grp.sort_values("joint_id").copy()
        root_xyz = compute_frame_root_from_abs_frame(g, root_mode=root_mode, root_joint_id=root_joint_id, root_joint_name=root_joint_name)

        for _, row in g.iterrows():
            valid = int(row["valid"])
            if valid == 1 and root_xyz is not None and not pd.isna(row["x"]) and not pd.isna(row["y"]) and not pd.isna(row["z"]):
                xyz_abs = np.array([row["x"], row["y"], row["z"]], dtype=float)
                xyz_rel = xyz_abs - root_xyz
                root_vals = root_xyz
            else:
                xyz_rel = np.array([np.nan, np.nan, np.nan], dtype=float)
                root_vals = np.array([np.nan, np.nan, np.nan], dtype=float) if root_xyz is None else root_xyz
                if root_xyz is None:
                    valid = 0

            rows.append({
                "frame_id": int(frame_id),
                "joint_id": int(row["joint_id"]),
                "joint_name": row["joint_name"],
                "root_mode": root_mode,
                "root_joint_id": np.nan if resolved_root_joint_id is None else int(resolved_root_joint_id),
                "root_joint_name": "" if root_joint_name is None else str(root_joint_name),
                "root_x": np.nan if np.isnan(root_vals[0]) else float(root_vals[0]),
                "root_y": np.nan if np.isnan(root_vals[1]) else float(root_vals[1]),
                "root_z": np.nan if np.isnan(root_vals[2]) else float(root_vals[2]),
                "x_rel": np.nan if np.isnan(xyz_rel[0]) else float(xyz_rel[0]),
                "y_rel": np.nan if np.isnan(xyz_rel[1]) else float(xyz_rel[1]),
                "z_rel": np.nan if np.isnan(xyz_rel[2]) else float(xyz_rel[2]),
                "x_abs": np.nan if pd.isna(row["x"]) else float(row["x"]),
                "y_abs": np.nan if pd.isna(row["y"]) else float(row["y"]),
                "z_abs": np.nan if pd.isna(row["z"]) else float(row["z"]),
                "valid": int(valid),
            })

    return pd.DataFrame(rows, columns=[
        "frame_id", "joint_id", "joint_name", "root_mode", "root_joint_id", "root_joint_name",
        "root_x", "root_y", "root_z",
        "x_rel", "y_rel", "z_rel",
        "x_abs", "y_abs", "z_abs",
        "valid",
    ])




def _resolve_ground_align_joint_names(ground_align_joint_names=None):
    default_names = [
        "left_heel", "right_heel",
        "left_ankle", "right_ankle",
        "left_foot_index", "right_foot_index",
    ]
    if ground_align_joint_names is None:
        return default_names
    names = [str(x).strip() for x in ground_align_joint_names if str(x).strip() != ""]
    return names if names else default_names


def align_abs_dataframe_ground_z(
    df_abs: pd.DataFrame,
    enabled: bool = False,
    ground_align_joint_names=None,
    statistic: str = "mean",
    target_z: float = 0.0,
):
    df = df_abs.copy()
    if not enabled:
        return df, 0.0

    joint_names = _resolve_ground_align_joint_names(ground_align_joint_names)
    statistic = str(statistic).lower().strip()
    target_z = float(target_z)

    df["z"] = pd.to_numeric(df["z"], errors="coerce")
    valid_col = pd.to_numeric(df.get("valid", 1), errors="coerce").fillna(0).astype(int)
    mask = df["joint_name"].astype(str).isin(joint_names) & df["z"].notna() & (valid_col == 1)
    z_samples = df.loc[mask, "z"].to_numpy(dtype=float)

    if len(z_samples) == 0:
        return df, 0.0

    if statistic == "median":
        reference_z = float(np.median(z_samples))
    elif statistic == "p5":
        reference_z = float(np.percentile(z_samples, 5))
    elif statistic == "p10":
        reference_z = float(np.percentile(z_samples, 10))
    else:
        reference_z = float(np.mean(z_samples))

    shift = reference_z - target_z
    if abs(shift) > 1e-12:
        # Keep the operation in pandas space to avoid backend-specific
        # read-only ndarray issues during in-place numpy writes.
        finite_mask = df["z"].notna()
        if finite_mask.any():
            df.loc[finite_mask, "z"] = pd.to_numeric(df.loc[finite_mask, "z"], errors="coerce") - shift
    return df, shift
def temporal_filter_pose3d_abs_csv(
    input_pose3d_abs_csv_path: str,
    output_pose3d_abs_csv_path: str,
    output_pose3d_relative_csv_path: str,
    method: str = "median_then_mean",
    window_size: int = 5,
    relative_root_mode: str = "pelvis_midpoint",
    root_joint_id: int | None = None,
    root_joint_name: str | None = None,
    ground_align_enabled: bool = False,
    ground_align_joint_names=None,
    ground_align_statistic: str = "mean",
    ground_align_target_z: float = 0.0,
    extra_abs_output_csv_path: str | None = None,
):
    input_pose3d_abs_csv_path = Path(input_pose3d_abs_csv_path)
    output_pose3d_abs_csv_path = Path(output_pose3d_abs_csv_path)
    output_pose3d_relative_csv_path = Path(output_pose3d_relative_csv_path)

    if not input_pose3d_abs_csv_path.exists():
        raise FileNotFoundError(f"未找到输入文件: {input_pose3d_abs_csv_path}")

    output_pose3d_abs_csv_path.parent.mkdir(parents=True, exist_ok=True)
    output_pose3d_relative_csv_path.parent.mkdir(parents=True, exist_ok=True)

    df_abs = pd.read_csv(input_pose3d_abs_csv_path)
    df_abs_filtered = smooth_pose3d_abs_dataframe(df_abs=df_abs, method=method, window_size=window_size)
    df_abs_filtered, ground_shift = align_abs_dataframe_ground_z(
        df_abs_filtered,
        enabled=ground_align_enabled,
        ground_align_joint_names=ground_align_joint_names,
        statistic=ground_align_statistic,
        target_z=ground_align_target_z,
    )
    df_rel_filtered = build_relative_pose3d_dataframe(
        df_abs=df_abs_filtered,
        root_mode=relative_root_mode,
        root_joint_id=root_joint_id,
        root_joint_name=root_joint_name,
    )

    df_abs_filtered.to_csv(output_pose3d_abs_csv_path, index=False, encoding="utf-8")
    df_rel_filtered.to_csv(output_pose3d_relative_csv_path, index=False, encoding="utf-8")

    if extra_abs_output_csv_path is not None and str(extra_abs_output_csv_path).strip() != "":
        extra_abs_output_csv_path = Path(extra_abs_output_csv_path)
        extra_abs_output_csv_path.parent.mkdir(parents=True, exist_ok=True)
        df_abs_filtered.to_csv(extra_abs_output_csv_path, index=False, encoding="utf-8")
        print(f"pose3d_abs_filtered_ground_aligned.csv 已保存到: {extra_abs_output_csv_path}")

    if ground_align_enabled:
        print(f"ground z alignment enabled, z shift = {ground_shift:.6f} m")
    print(f"pose3d_abs_filtered.csv 已保存到: {output_pose3d_abs_csv_path}")
    print(f"pose3d_relative_filtered.csv 已保存到: {output_pose3d_relative_csv_path}")
    return str(output_pose3d_abs_csv_path), str(output_pose3d_relative_csv_path)


def ground_align_pose3d_abs_csv(
    input_pose3d_abs_csv_path: str,
    output_pose3d_abs_csv_path: str,
    output_pose3d_relative_csv_path: str,
    relative_root_mode: str = "pelvis_midpoint",
    root_joint_id: int | None = None,
    root_joint_name: str | None = None,
    ground_align_enabled: bool = True,
    ground_align_joint_names=None,
    ground_align_statistic: str = "mean",
    ground_align_target_z: float = 0.0,
    extra_abs_output_csv_path: str | None = None,
):
    """对绝对 3D 姿态数据做地面对齐（不做时间滤波），并生成相对姿态。"""
    input_pose3d_abs_csv_path = Path(input_pose3d_abs_csv_path)
    output_pose3d_abs_csv_path = Path(output_pose3d_abs_csv_path)
    output_pose3d_relative_csv_path = Path(output_pose3d_relative_csv_path)

    if not input_pose3d_abs_csv_path.exists():
        raise FileNotFoundError(f"未找到输入文件: {input_pose3d_abs_csv_path}")

    output_pose3d_abs_csv_path.parent.mkdir(parents=True, exist_ok=True)
    output_pose3d_relative_csv_path.parent.mkdir(parents=True, exist_ok=True)

    df_abs = pd.read_csv(input_pose3d_abs_csv_path)

    df_abs_aligned, ground_shift = align_abs_dataframe_ground_z(
        df_abs,
        enabled=ground_align_enabled,
        ground_align_joint_names=ground_align_joint_names,
        statistic=ground_align_statistic,
        target_z=ground_align_target_z,
    )

    df_rel = build_relative_pose3d_dataframe(
        df_abs=df_abs_aligned,
        root_mode=relative_root_mode,
        root_joint_id=root_joint_id,
        root_joint_name=root_joint_name,
    )

    df_abs_aligned.to_csv(output_pose3d_abs_csv_path, index=False, encoding="utf-8")
    df_rel.to_csv(output_pose3d_relative_csv_path, index=False, encoding="utf-8")

    if extra_abs_output_csv_path is not None and str(extra_abs_output_csv_path).strip() != "":
        extra_abs_output_csv_path = Path(extra_abs_output_csv_path)
        extra_abs_output_csv_path.parent.mkdir(parents=True, exist_ok=True)
        df_abs_aligned.to_csv(extra_abs_output_csv_path, index=False, encoding="utf-8")
        print(f"pose3d_abs_ground_aligned 已额外保存到: {extra_abs_output_csv_path}")

    if ground_align_enabled:
        print(f"ground z alignment enabled, z shift = {ground_shift:.6f} m")
    print(f"pose3d_abs_ground_aligned.csv 已保存到: {output_pose3d_abs_csv_path}")
    print(f"pose3d_relative.csv 已保存到: {output_pose3d_relative_csv_path}")
    return str(output_pose3d_abs_csv_path), str(output_pose3d_relative_csv_path)


_WIDE_JOINT_ORDER = [
    "body_com",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
    "left_shoulder", "right_shoulder",
]


def _build_wide_columns():
    cols = ["frame_id"]
    for joint in _WIDE_JOINT_ORDER:
        cols.extend([f"{joint}_x", f"{joint}_y", f"{joint}_z"])
    return cols


def export_pose3d_wide_csv(
    input_pose3d_abs_csv_path: str,
    output_wide_csv_path: str,
):
    """将 ground-aligned 长表 CSV 转换为宽表 CSV 并保存。"""
    input_pose3d_abs_csv_path = Path(input_pose3d_abs_csv_path)
    output_wide_csv_path = Path(output_wide_csv_path)

    if not input_pose3d_abs_csv_path.exists():
        raise FileNotFoundError(f"未找到输入文件: {input_pose3d_abs_csv_path}")

    output_wide_csv_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_pose3d_abs_csv_path)

    required_cols = ["frame_id", "joint_name", "x", "y", "z"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"输入 CSV 缺少必要列: {col}")

    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df["z"] = pd.to_numeric(df["z"], errors="coerce")

    frames = sorted(df["frame_id"].unique())
    rows = []
    for frame_id in frames:
        frame_df = df[df["frame_id"] == frame_id]
        row = {"frame_id": int(frame_id)}
        for joint in _WIDE_JOINT_ORDER:
            jd = frame_df[frame_df["joint_name"] == joint]
            if len(jd) == 1:
                row[f"{joint}_x"] = float(jd["x"].iloc[0]) if pd.notna(jd["x"].iloc[0]) else ""
                row[f"{joint}_y"] = float(jd["y"].iloc[0]) if pd.notna(jd["y"].iloc[0]) else ""
                row[f"{joint}_z"] = float(jd["z"].iloc[0]) if pd.notna(jd["z"].iloc[0]) else ""
            else:
                row[f"{joint}_x"] = ""
                row[f"{joint}_y"] = ""
                row[f"{joint}_z"] = ""
        rows.append(row)

    wide_df = pd.DataFrame(rows, columns=_build_wide_columns())
    wide_df.to_csv(output_wide_csv_path, index=False, encoding="utf-8")
    print(f"pose3d_wide.csv 已保存到: {output_wide_csv_path}")
    return str(output_wide_csv_path)
