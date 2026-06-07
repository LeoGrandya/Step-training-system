import json
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np


DEFAULT_WORLD_POINTS_XY = np.array(
    [
        [0.0, 0.0],
        [2.7, 0.0],
        [2.7, 2.7],
        [0.0, 2.7],
    ],
    dtype=np.float64,
)

CONTROL_POINT_LABELS = ["TL", "TR", "BR", "BL"]
CONTROL_POINT_ORDER = ["top_left", "top_right", "bottom_right", "bottom_left"]


def _load_json(json_path: str) -> dict:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(json_path: str, data: dict) -> None:
    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _read_frame(video_path: str, frame_index: int = 0) -> np.ndarray:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        raise ValueError(f"视频无法读取总帧数: {video_path}")

    if frame_index < 0 or frame_index >= total_frames:
        cap.release()
        raise ValueError(f"frame_index={frame_index} 超出范围，总帧数={total_frames}")

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise ValueError(f"无法读取视频帧: {video_path}, frame={frame_index}")
    return frame


def _as_np(data, dtype=np.float64) -> np.ndarray:
    return np.asarray(data, dtype=dtype)


def _order_quad_points(pts: np.ndarray) -> np.ndarray:
    pts = _as_np(pts, np.float64).reshape(-1, 2)
    if pts.shape[0] != 4:
        raise ValueError("排序四边形角点时，输入点数必须为 4")

    sums = pts[:, 0] + pts[:, 1]
    diffs = pts[:, 0] - pts[:, 1]

    idx_tl = int(np.argmin(sums))
    idx_br = int(np.argmax(sums))
    idx_tr = int(np.argmax(diffs))
    idx_bl = int(np.argmin(diffs))

    idxs = [idx_tl, idx_tr, idx_br, idx_bl]
    if len(set(idxs)) == 4:
        return pts[idxs]

    ys = pts[:, 1]
    top_ids = np.argsort(ys)[:2]
    bottom_ids = np.argsort(ys)[-2:]
    top = pts[top_ids]
    bottom = pts[bottom_ids]
    top = top[np.argsort(top[:, 0])]
    bottom = bottom[np.argsort(bottom[:, 0])]
    return np.array([top[0], top[1], bottom[1], bottom[0]], dtype=np.float64)


def _compose_manual_canvas(
    frame: np.ndarray,
    points: np.ndarray,
    world_points_xy: np.ndarray,
    title: str,
    selected_idx: int | None,
    dragging: bool,
    click_radius: int,
    show_help: bool,
) -> np.ndarray:
    vis = frame.copy()
    points = np.asarray(points, dtype=np.float64).reshape(-1, 2) if len(points) > 0 else np.zeros((0, 2), dtype=np.float64)

    if len(points) >= 2:
        poly_pts = np.round(points).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(vis, [poly_pts], False if len(points) < 4 else True, (255, 0, 0), 2)

    for idx, pt in enumerate(points):
        x, y = int(round(pt[0])), int(round(pt[1]))
        color = (0, 165, 255) if idx == selected_idx else (0, 0, 255)
        radius = 12 if idx == selected_idx else 9
        thickness = -1 if dragging and idx == selected_idx else 2
        cv2.circle(vis, (x, y), radius, color, thickness)
        text = f"{idx + 1}:{CONTROL_POINT_LABELS[idx]} ({world_points_xy[idx, 0]:.2f},{world_points_xy[idx, 1]:.2f})"
        cv2.putText(vis, text, (x + 10, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

    cv2.putText(vis, title, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(vis, f"click radius: {click_radius}px", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

    if len(points) < 4:
        next_idx = len(points)
        prompt = f"请按顺序点击第 {next_idx + 1} 个点: {CONTROL_POINT_LABELS[next_idx]} / {CONTROL_POINT_ORDER[next_idx]}"
        cv2.putText(vis, prompt, (20, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
    else:
        prompt = "4个点已完成：可拖动修正，按 Enter/空格 确认"
        cv2.putText(vis, prompt, (20, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

    if show_help:
        help_lines = [
            "Mouse: click in order TL -> TR -> BR -> BL",
            "Mouse: drag an existing point to adjust",
            "1/2/3/4: select point, then click elsewhere to move it",
            "Backspace/Z: undo last   C: clear   R: reset",
            "Enter/Space: confirm   Esc/Q: cancel",
        ]
        y0 = 125
        for i, line in enumerate(help_lines):
            cv2.putText(vis, line, (20, y0 + i * 26), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 0), 2, cv2.LINE_AA)

    return vis


def _interactive_pick_points(
    frame: np.ndarray,
    world_points_xy: np.ndarray,
    title: str,
    review_cfg: Dict,
    initial_points: np.ndarray | None = None,
) -> np.ndarray:
    display_scale = float(review_cfg.get("display_scale", 1.0))
    display_scale = max(display_scale, 0.1)
    click_radius = int(review_cfg.get("click_radius_px", 30))
    show_help = bool(review_cfg.get("show_help", True))
    win_name = str(review_cfg.get("window_name_prefix", "ground_control_manual")) + " - " + title

    points: List[List[float]] = []
    if initial_points is not None:
        init = _as_np(initial_points, np.float64).reshape(-1, 2)
        if init.shape[0] != 4:
            raise ValueError("initial_points 必须是 4x2")
        points = init.tolist()
    reset_points = [p[:] for p in points]

    state = {
        "selected_idx": None,
        "dragging": False,
        "confirmed": False,
        "cancelled": False,
    }

    def _to_orig_xy(x_disp: int, y_disp: int) -> Tuple[float, float]:
        return float(x_disp / display_scale), float(y_disp / display_scale)

    def _find_nearest_idx(x_orig: float, y_orig: float) -> Tuple[int | None, float]:
        if len(points) == 0:
            return None, float("inf")
        arr = np.asarray(points, dtype=np.float64)
        dists = np.linalg.norm(arr - np.array([x_orig, y_orig], dtype=np.float64), axis=1)
        idx = int(np.argmin(dists))
        return idx, float(dists[idx])

    def _mouse_callback(event, x, y, flags, param):
        x_orig, y_orig = _to_orig_xy(x, y)

        if event == cv2.EVENT_LBUTTONDOWN:
            idx, dist = _find_nearest_idx(x_orig, y_orig)
            if idx is not None and dist <= click_radius:
                state["selected_idx"] = idx
                state["dragging"] = True
                points[idx] = [x_orig, y_orig]
                return

            if state["selected_idx"] is not None and len(points) == 4:
                points[state["selected_idx"]] = [x_orig, y_orig]
                state["dragging"] = True
                return

            if len(points) < 4:
                points.append([x_orig, y_orig])
                state["selected_idx"] = len(points) - 1
                state["dragging"] = True

        elif event == cv2.EVENT_MOUSEMOVE and state["dragging"] and state["selected_idx"] is not None:
            idx = state["selected_idx"]
            if 0 <= idx < len(points):
                points[idx] = [x_orig, y_orig]

        elif event == cv2.EVENT_LBUTTONUP:
            if state["dragging"] and state["selected_idx"] is not None:
                idx = state["selected_idx"]
                if 0 <= idx < len(points):
                    points[idx] = [x_orig, y_orig]
            state["dragging"] = False

    try:
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(win_name, _mouse_callback)
    except cv2.error as e:
        raise RuntimeError(
            "无法创建人工标点窗口。若在无图形界面的环境运行，请关闭人工标点或改为加载已保存点位。"
        ) from e

    while True:
        pts_array = np.asarray(points, dtype=np.float64).reshape(-1, 2) if len(points) > 0 else np.zeros((0, 2), dtype=np.float64)
        vis = _compose_manual_canvas(
            frame=frame,
            points=pts_array,
            world_points_xy=world_points_xy,
            title=title,
            selected_idx=state["selected_idx"],
            dragging=state["dragging"],
            click_radius=click_radius,
            show_help=show_help,
        )

        if abs(display_scale - 1.0) > 1e-6:
            vis = cv2.resize(vis, None, fx=display_scale, fy=display_scale, interpolation=cv2.INTER_LINEAR)

        cv2.imshow(win_name, vis)
        key = cv2.waitKey(20) & 0xFF

        if key in (13, 10, 32):
            if len(points) == 4:
                state["confirmed"] = True
                break
        elif key in (27, ord("q"), ord("Q")):
            state["cancelled"] = True
            break
        elif key in (8, 127, ord("z"), ord("Z")):
            if len(points) > 0:
                points.pop()
                if state["selected_idx"] is not None and state["selected_idx"] >= len(points):
                    state["selected_idx"] = len(points) - 1 if len(points) > 0 else None
                state["dragging"] = False
        elif key in (ord("c"), ord("C")):
            points.clear()
            state["selected_idx"] = None
            state["dragging"] = False
        elif key in (ord("r"), ord("R")):
            points = [p[:] for p in reset_points]
            state["selected_idx"] = None
            state["dragging"] = False
        elif key in (ord("1"), ord("2"), ord("3"), ord("4")):
            idx = int(chr(key)) - 1
            if idx < len(points):
                state["selected_idx"] = idx

    cv2.destroyWindow(win_name)

    if state["cancelled"] and not state["confirmed"]:
        raise RuntimeError("人工标点已取消，流程终止。")

    if len(points) != 4:
        raise RuntimeError(f"人工标点失败：当前点数为 {len(points)}，不是 4 个。")

    return np.asarray(points, dtype=np.float64).reshape(4, 2)


def _solve_camera_pose(world_points_xy: np.ndarray, image_points: np.ndarray, K: np.ndarray, dist: np.ndarray):
    obj = np.hstack([world_points_xy.astype(np.float64), np.zeros((world_points_xy.shape[0], 1), dtype=np.float64)])
    img = image_points.astype(np.float64).reshape(-1, 1, 2)
    dist = dist.reshape(-1, 1).astype(np.float64)

    success, rvec, tvec = cv2.solvePnP(
        obj,
        img,
        K.astype(np.float64),
        dist,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not success:
        raise RuntimeError("solvePnP 求相机位姿失败")

    R, _ = cv2.Rodrigues(rvec)
    t = tvec.reshape(3, 1)
    C = -R.T @ t
    P = K @ np.hstack([R, t])
    return R, t, C.reshape(3), P


def _compute_reproj_error(world_points_xy: np.ndarray, image_points: np.ndarray, K: np.ndarray, dist: np.ndarray, R: np.ndarray, t: np.ndarray):
    obj = np.hstack([world_points_xy.astype(np.float64), np.zeros((world_points_xy.shape[0], 1), dtype=np.float64)])
    rvec, _ = cv2.Rodrigues(R)
    proj, _ = cv2.projectPoints(obj, rvec, t, K.astype(np.float64), dist.reshape(-1, 1).astype(np.float64))
    proj = proj.reshape(-1, 2)
    err = np.linalg.norm(proj - image_points.reshape(-1, 2), axis=1)
    return float(np.mean(err)), proj


def _build_camera_record(name: str, K: np.ndarray, dist: np.ndarray, R: np.ndarray, t: np.ndarray, C: np.ndarray, P: np.ndarray, H_img_to_world: np.ndarray, H_world_to_img: np.ndarray, image_points: np.ndarray, reproj_error_px: float) -> dict:
    return {
        "camera_name": name,
        "K": K.tolist(),
        "dist": dist.reshape(-1).tolist(),
        "R": R.tolist(),
        "t": t.reshape(-1).tolist(),
        "camera_center_world": C.reshape(-1).tolist(),
        "projection_matrix": P.tolist(),
        "homography_image_to_world": H_img_to_world.tolist(),
        "homography_world_to_image": H_world_to_img.tolist(),
        "control_points_image": image_points.reshape(-1, 2).tolist(),
        "control_points_order": CONTROL_POINT_ORDER,
        "mean_control_reproj_error_px": float(reproj_error_px),
    }


def _draw_confirmed_points_image(
    frame: np.ndarray,
    confirmed_points: np.ndarray,
    world_points_xy: np.ndarray,
    save_path: str,
    title: str,
) -> None:
    vis = _compose_manual_canvas(
        frame=frame,
        points=confirmed_points,
        world_points_xy=world_points_xy,
        title=title,
        selected_idx=None,
        dragging=False,
        click_radius=20,
        show_help=False,
    )
    save_path = str(save_path)
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(save_path, vis)


def _load_saved_points_if_available(json_path: str, frame_index: int, world_points_xy: np.ndarray) -> Tuple[np.ndarray, np.ndarray] | None:
    json_file = Path(json_path)
    if not json_file.exists():
        return None

    data = _load_json(str(json_file))
    left_points = _as_np(data.get("left_points", []), np.float64).reshape(-1, 2)
    right_points = _as_np(data.get("right_points", []), np.float64).reshape(-1, 2)
    saved_world = _as_np(data.get("world_points_xy", []), np.float64).reshape(-1, 2) if data.get("world_points_xy") else None

    if left_points.shape != (4, 2) or right_points.shape != (4, 2):
        raise ValueError(f"已保存点位文件格式不正确: {json_path}")

    if saved_world is not None and saved_world.shape == (4, 2):
        if np.max(np.abs(saved_world - world_points_xy)) > 1e-6:
            print("[警告] 已保存点位文件中的 world_points_xy 与当前 user_params.py 不一致，已按当前配置继续。")

    saved_frame_index = data.get("frame_index")
    if saved_frame_index is not None and int(saved_frame_index) != int(frame_index):
        print(f"[提示] 已保存点位来自 frame_index={saved_frame_index}，当前配置为 {frame_index}。由于是同机位复用，将继续使用保存点位。")

    print(f"已加载保存点位: {json_path}")
    return left_points, right_points


def _save_confirmed_points_json(
    json_path: str,
    frame_index: int,
    world_points_xy: np.ndarray,
    left_points: np.ndarray,
    right_points: np.ndarray,
    left_video: str,
    right_video: str,
    left_frame_shape: Tuple[int, int, int],
    right_frame_shape: Tuple[int, int, int],
) -> None:
    data = {
        "frame_index": int(frame_index),
        "control_points_order": CONTROL_POINT_ORDER,
        "world_points_xy": world_points_xy.reshape(-1, 2).tolist(),
        "left_points": left_points.reshape(-1, 2).tolist(),
        "right_points": right_points.reshape(-1, 2).tolist(),
        "left_video": str(left_video),
        "right_video": str(right_video),
        "left_frame_shape": list(left_frame_shape),
        "right_frame_shape": list(right_frame_shape),
    }
    _save_json(json_path, data)
    print(f"人工标点结果已保存到: {json_path}")


def build_ground_homography_summary(
    stereo_params_json: str,
    left_video: str,
    right_video: str,
    ground_cfg: Dict,
    output_json_path: str,
) -> Dict:
    stereo = _load_json(stereo_params_json)

    K1 = _as_np(stereo["K1"])
    K2 = _as_np(stereo["K2"])
    dist1 = _as_np(stereo.get("dist1", [0, 0, 0, 0, 0]))
    dist2 = _as_np(stereo.get("dist2", [0, 0, 0, 0, 0]))

    frame_index = int(ground_cfg.get("frame_index", 0))
    manual_cfg = ground_cfg.get("manual_annotation", {})
    debug_cfg = ground_cfg.get("debug", {})
    debug_dir = Path(debug_cfg.get("debug_dir", Path(output_json_path).parent / "ground_control_debug"))
    save_debug = bool(debug_cfg.get("save_debug_images", True))

    if "world_points_xy_m" in ground_cfg:
        world_points_xy = _order_quad_points(_as_np(ground_cfg["world_points_xy_m"], np.float64))
    else:
        width_m = float(ground_cfg.get("width_m", ground_cfg.get("distance_m", 2.7)))
        height_m = float(ground_cfg.get("height_m", ground_cfg.get("distance_m", 2.7)))
        world_points_xy = np.array(
            [
                [0.0, 0.0],
                [width_m, 0.0],
                [width_m, height_m],
                [0.0, height_m],
            ],
            dtype=np.float64,
        )

    left_frame = _read_frame(left_video, frame_index=frame_index)
    right_frame = _read_frame(right_video, frame_index=frame_index)

    points_json_path = str(manual_cfg.get("points_json_path", str(debug_dir / "manual_control_points.json")))
    reuse_saved_points = bool(manual_cfg.get("reuse_saved_points", True))
    force_repick = bool(manual_cfg.get("force_repick", False))
    save_points_json = bool(manual_cfg.get("save_points_json", True))
    use_saved_as_initial = bool(manual_cfg.get("use_saved_as_initial_when_repick", True))

    loaded = None
    initial_left = None
    initial_right = None
    point_source = "manual_new"

    if reuse_saved_points:
        loaded = _load_saved_points_if_available(points_json_path, frame_index, world_points_xy)
        if loaded is not None and not force_repick:
            left_points, right_points = loaded
            point_source = "saved_json"
        elif loaded is not None and force_repick and use_saved_as_initial:
            initial_left, initial_right = loaded

    if loaded is None or force_repick:
        if force_repick and loaded is not None:
            print("已开启 force_repick=True：将打开窗口重新人工标点，并用旧点位作为初始点。")
        else:
            print("未找到可复用点位：请在左右视频第0帧上依次手动点击 TL, TR, BR, BL 四个点。")

        left_points = _interactive_pick_points(
            frame=left_frame,
            world_points_xy=world_points_xy,
            title="LEFT manual annotation",
            review_cfg=manual_cfg,
            initial_points=initial_left,
        )
        right_points = _interactive_pick_points(
            frame=right_frame,
            world_points_xy=world_points_xy,
            title="RIGHT manual annotation",
            review_cfg=manual_cfg,
            initial_points=initial_right,
        )
        point_source = "manual_new" if loaded is None else "manual_repick"

        if save_points_json:
            _save_confirmed_points_json(
                json_path=points_json_path,
                frame_index=frame_index,
                world_points_xy=world_points_xy,
                left_points=left_points,
                right_points=right_points,
                left_video=left_video,
                right_video=right_video,
                left_frame_shape=left_frame.shape,
                right_frame_shape=right_frame.shape,
            )

    H_left_world_to_img = cv2.getPerspectiveTransform(world_points_xy.astype(np.float32), left_points.astype(np.float32))
    H_left_img_to_world = np.linalg.inv(H_left_world_to_img)

    H_right_world_to_img = cv2.getPerspectiveTransform(world_points_xy.astype(np.float32), right_points.astype(np.float32))
    H_right_img_to_world = np.linalg.inv(H_right_world_to_img)

    R1, t1, C1, P1 = _solve_camera_pose(world_points_xy, left_points, K1, dist1)
    R2, t2, C2, P2 = _solve_camera_pose(world_points_xy, right_points, K2, dist2)

    left_reproj_err, left_reproj_pts = _compute_reproj_error(world_points_xy, left_points, K1, dist1, R1, t1)
    right_reproj_err, right_reproj_pts = _compute_reproj_error(world_points_xy, right_points, K2, dist2, R2, t2)

    result = {
        "reconstruction_method": "ground_homography_rays",
        "reference_frame": "world_plane_from_manual_control_points",
        "world_frame": {
            "plane": "Z=0",
            "unit": "meter",
            "control_points_order": CONTROL_POINT_ORDER,
            "control_points_xy": world_points_xy.tolist(),
        },
        "control_points": {
            "frame_index": frame_index,
            "left_video": left_video,
            "right_video": right_video,
            "point_source": point_source,
            "left_points_confirmed": left_points.tolist(),
            "right_points_confirmed": right_points.tolist(),
            "points_json_path": str(points_json_path),
            "reuse_saved_points": reuse_saved_points,
            "force_repick": force_repick,
        },
        "left_camera": _build_camera_record(
            name="left",
            K=K1,
            dist=dist1,
            R=R1,
            t=t1,
            C=C1,
            P=P1,
            H_img_to_world=H_left_img_to_world,
            H_world_to_img=H_left_world_to_img,
            image_points=left_points,
            reproj_error_px=left_reproj_err,
        ),
        "right_camera": _build_camera_record(
            name="right",
            K=K2,
            dist=dist2,
            R=R2,
            t=t2,
            C=C2,
            P=P2,
            H_img_to_world=H_right_img_to_world,
            H_world_to_img=H_right_world_to_img,
            image_points=right_points,
            reproj_error_px=right_reproj_err,
        ),
        "stereo": {
            "baseline_from_world_pose_meter": float(np.linalg.norm(C1.reshape(3) - C2.reshape(3))),
            "image_size": stereo.get("image_size", None),
        },
    }

    output_json_path = Path(output_json_path)
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    if save_debug:
        debug_dir.mkdir(parents=True, exist_ok=True)
        _draw_confirmed_points_image(left_frame, left_points, world_points_xy, str(debug_dir / "left_manual_control_points.jpg"), "LEFT confirmed")
        _draw_confirmed_points_image(right_frame, right_points, world_points_xy, str(debug_dir / "right_manual_control_points.jpg"), "RIGHT confirmed")

        left_reproj_vis = left_frame.copy()
        right_reproj_vis = right_frame.copy()
        for obs, rp in zip(left_points, left_reproj_pts):
            cv2.circle(left_reproj_vis, tuple(np.round(obs).astype(int)), 8, (0, 255, 0), 2)
            cv2.circle(left_reproj_vis, tuple(np.round(rp).astype(int)), 4, (0, 0, 255), -1)
        for obs, rp in zip(right_points, right_reproj_pts):
            cv2.circle(right_reproj_vis, tuple(np.round(obs).astype(int)), 8, (0, 255, 0), 2)
            cv2.circle(right_reproj_vis, tuple(np.round(rp).astype(int)), 4, (0, 0, 255), -1)
        cv2.imwrite(str(debug_dir / "left_control_points_reprojection.jpg"), left_reproj_vis)
        cv2.imwrite(str(debug_dir / "right_control_points_reprojection.jpg"), right_reproj_vis)

    return result
