import cv2

from pose3d_pkg.io.video_filter import apply_frame_filter


class StereoVideoReader:
    """最小双视频同步读取器，支持可选视频滤波。"""

    def __init__(self, left_path: str, right_path: str, filter_cfg=None):
        self.left_path = left_path
        self.right_path = right_path
        self.filter_cfg = filter_cfg

        self.left_cap = cv2.VideoCapture(left_path)
        self.right_cap = cv2.VideoCapture(right_path)

        if not self.left_cap.isOpened():
            raise ValueError(f"无法打开左视频: {left_path}")
        if not self.right_cap.isOpened():
            raise ValueError(f"无法打开右视频: {right_path}")

        self.frame_id = 0
        self.left_info = self._get_video_info(self.left_cap, "left")
        self.right_info = self._get_video_info(self.right_cap, "right")

    @staticmethod
    def _get_video_info(cap: cv2.VideoCapture, name: str) -> dict:
        return {
            "name": name,
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": float(cap.get(cv2.CAP_PROP_FPS)),
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        }

    def print_info(self) -> None:
        print("=== 左视频信息 ===")
        print(self.left_info)
        print("=== 右视频信息 ===")
        print(self.right_info)
        if self.left_info["fps"] != self.right_info["fps"]:
            print("警告：左右视频 FPS 不一致。")
        if self.left_info["frame_count"] != self.right_info["frame_count"]:
            print("警告：左右视频总帧数不一致，将以较短视频为准。")
        if self.filter_cfg and self.filter_cfg.get("enabled", False):
            print(f"视频滤波已启用: method={self.filter_cfg.get('method', 'none')}")

    def read(self):
        ret_l, frame_l = self.left_cap.read()
        ret_r, frame_r = self.right_cap.read()
        if not ret_l or not ret_r:
            return False, self.frame_id, None, None

        if self.filter_cfg and self.filter_cfg.get("enabled", False):
            frame_l = apply_frame_filter(frame_l, self.filter_cfg)
            frame_r = apply_frame_filter(frame_r, self.filter_cfg)

        fid = self.frame_id
        self.frame_id += 1
        return True, fid, frame_l, frame_r

    def release(self) -> None:
        self.left_cap.release()
        self.right_cap.release()


def count_video_frames(video_path: str) -> int:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return frame_count
