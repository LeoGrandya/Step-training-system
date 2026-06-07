"""双机位视频同步（音轨互相关 + ffmpeg）与对齐双路抽帧（OpenCV）。

运行时必需：web_1/backend/analysis/sync_service.py 调用 run_sync；Streamlit/CLI 在 _archive 中调用本模块。
原分散逻辑已集中于此；离线 GUI/CLI 入口见 _archive/video_sync_tools/。
"""

from __future__ import annotations

import argparse
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable, Protocol, cast

import cv2
import numpy as np
from scipy.io import wavfile
from scipy.signal import correlate, correlation_lags

# =============================================================================
# 配置
# =============================================================================
GUI_OUTPUT_DIR_FIRST = Path(r"D:\lookfeet\sync_output\camera_a")
GUI_OUTPUT_DIR_SECOND = Path(r"D:\lookfeet\sync_output\camera_b")
PHASE_P0, PHASE_P1, PHASE_P2, PHASE_P3, PHASE_P4 = 0.0, 0.10, 0.20, 0.26, 0.63

# =============================================================================
# 进度
# =============================================================================
class ProgressSink(Protocol):
    def set_phase(self, desc: str) -> None: ...

    def set_overall(self, value: float) -> None: ...


class NullProgress:
    def set_phase(self, desc: str) -> None:
        pass

    def set_overall(self, value: float) -> None:
        pass


class TqdmProgress:
    def __init__(self) -> None:
        from tqdm import tqdm

        self._p = tqdm(
            total=1000,
            desc="准备",
            unit="‰",
            ascii=True,
            mininterval=0.12,
            file=sys.stderr,
        )

    def set_phase(self, desc: str) -> None:
        self._p.set_description(desc, refresh=False)

    def set_overall(self, value: float) -> None:
        v = max(0.0, min(1.0, value))
        self._p.n = int(1000 * v)
        self._p.refresh()


class QueueProgress:
    def __init__(self, q: "queue.Queue[tuple[str, object]]") -> None:
        self._q = q

    def set_phase(self, desc: str) -> None:
        self._q.put(("phase", desc))

    def set_overall(self, value: float) -> None:
        self._q.put(("overall", max(0.0, min(1.0, value))))


# =============================================================================
# FFmpeg / ffprobe
# =============================================================================
_SUBPROCESS_TEXT = {"encoding": "utf-8", "errors": "replace"}
_FFMPEG_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+\.?\d*)")
_ffprobe_exe: str | None = None


def _time_token_to_seconds(m: re.Match[str]) -> float:
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600.0 + mi * 60.0 + s


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        sys.stderr.write(
            "未找到 ffmpeg。请安装 FFmpeg 并加入 PATH：https://ffmpeg.org/download.html\n"
        )
        sys.exit(1)


def get_duration_seconds(video: Path) -> float:
    global _ffprobe_exe
    if _ffprobe_exe is None:
        _ffprobe_exe = shutil.which("ffprobe")
        if _ffprobe_exe is None:
            raise RuntimeError("需要 ffprobe（通常随 FFmpeg 一起安装）")
    r = subprocess.run(
        [
            _ffprobe_exe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        capture_output=True,
        text=True,
        **_SUBPROCESS_TEXT,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr or "ffprobe 失败")
    return float(r.stdout.strip())


def _run_ffmpeg_quiet(ff_args: list[str]) -> None:
    cmd = ["ffmpeg", "-y", "-nostdin", "-loglevel", "error"] + ff_args
    r = subprocess.run(
        cmd, capture_output=True, text=True, **_SUBPROCESS_TEXT
    )
    if r.returncode != 0:
        sys.stderr.write(r.stderr or r.stdout or "ffmpeg failed\n")
        raise RuntimeError("ffmpeg 执行失败")


def run_ffmpeg_with_progress(
    ff_args: list[str],
    *,
    duration_sec: float,
    progress: ProgressSink,
    range_start: float,
    range_end: float,
) -> None:
    if isinstance(progress, NullProgress):
        _run_ffmpeg_quiet(ff_args)
        progress.set_overall(range_end)
        return

    dur = max(0.01, float(duration_sec))
    span = max(0.0, range_end - range_start)
    cmd = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "info",
    ] + ff_args
    p = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        **_SUBPROCESS_TEXT,
    )
    assert p.stderr is not None
    last_report = -1.0
    last_wall = 0.0
    err_tail: deque[str] = deque(maxlen=40)
    for line in p.stderr:
        err_tail.append(line)
        m = _FFMPEG_TIME_RE.search(line)
        if not m:
            continue
        t = _time_token_to_seconds(m)
        frac = min(1.0, t / dur)
        if frac < last_report:
            continue
        now = time.monotonic()
        if frac - last_report < 0.003 and now - last_wall < 0.12 and frac < 0.999:
            continue
        last_report = frac
        last_wall = now
        progress.set_overall(range_start + frac * span)
    p.wait()
    if p.returncode != 0:
        sys.stderr.write("".join(err_tail) or "ffmpeg failed\n")
        raise RuntimeError("ffmpeg 执行失败")
    progress.set_overall(range_end)


# =============================================================================
# 音轨与互相关
# =============================================================================
def load_wav_mono_float(wav_path: Path) -> tuple[int, np.ndarray]:
    fs, data = wavfile.read(wav_path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    x = data.astype(np.float32, copy=False)
    peak = float(np.max(np.abs(x))) + 1e-9
    x /= peak
    return fs, x


def estimate_lag_seconds(
    wav_a: Path,
    wav_b: Path,
    *,
    max_seconds: float = 120.0,
) -> tuple[float, float]:
    fs_a, a = load_wav_mono_float(wav_a)
    fs_b, b = load_wav_mono_float(wav_b)
    if fs_a != fs_b:
        raise RuntimeError("内部错误：采样率不一致")

    fs = fs_a
    max_n = int(max_seconds * fs)
    if len(a) > max_n:
        a = a[:max_n]
    if len(b) > max_n:
        b = b[:max_n]

    a = a - np.mean(a)
    b = b - np.mean(b)

    c = correlate(a, b, mode="full", method="fft")
    lags = correlation_lags(len(a), len(b), mode="full")
    peak_i = int(np.argmax(c))
    lag_samples = int(lags[peak_i])

    if lag_samples >= 0:
        return lag_samples / fs, 0.0
    return 0.0, (-lag_samples) / fs


def extract_audio_wav(
    video_path: Path,
    wav_path: Path,
    *,
    sample_rate: int = 8000,
    progress: ProgressSink,
    range_start: float,
    range_end: float,
    duration_sec: float,
) -> None:
    run_ffmpeg_with_progress(
        [
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-acodec",
            "pcm_s16le",
            str(wav_path),
        ],
        duration_sec=duration_sec,
        progress=progress,
        range_start=range_start,
        range_end=range_end,
    )


def trim_and_encode(
    src: Path,
    dst: Path,
    *,
    skip_sec: float,
    duration_sec: float,
    video_codec: str = "libx264",
    crf: str = "20",
    audio_codec: str = "aac",
    video_mode: str = "reencode",
    progress: ProgressSink,
    range_start: float,
    range_end: float,
) -> None:
    """裁切对齐片段并写出。

    video_mode:
      - ``reencode``：libx264 + CRF（默认），会重编码，空间分辨率通常与源一致但为有损压缩。
      - ``copy``：``-c copy`` 流复制，不重编码，**在像素分辨率与压缩痕迹上最接近「原片截取」**；
        起止位置可能落在关键帧附近，个别容器若失败可改回 reencode。
    """
    skip_sec = max(0.0, float(skip_sec))
    duration_sec = max(0.01, float(duration_sec))
    dst.parent.mkdir(parents=True, exist_ok=True)
    vm = (video_mode or "reencode").strip().lower()
    if vm == "copy":
        # -ss 放在 -i 之后，便于流复制时在解码时间轴上裁切（略慢于放前面，但一般更稳）
        run_ffmpeg_with_progress(
            [
                "-i",
                str(src),
                "-ss",
                f"{skip_sec:.6f}",
                "-t",
                f"{duration_sec:.6f}",
                "-c",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                str(dst),
            ],
            duration_sec=duration_sec,
            progress=progress,
            range_start=range_start,
            range_end=range_end,
        )
        return
    run_ffmpeg_with_progress(
        [
            "-ss",
            f"{skip_sec:.6f}",
            "-i",
            str(src),
            "-t",
            f"{duration_sec:.6f}",
            "-c:v",
            video_codec,
            "-crf",
            crf,
            "-c:a",
            audio_codec,
            str(dst),
        ],
        duration_sec=duration_sec,
        progress=progress,
        range_start=range_start,
        range_end=range_end,
    )


# =============================================================================
# 同步主流程
# =============================================================================
def _cleanup_sync_temp(tdir: Path) -> None:
    for _ in range(10):
        try:
            shutil.rmtree(tdir, ignore_errors=False)
            return
        except OSError:
            time.sleep(0.1)
    shutil.rmtree(tdir, ignore_errors=True)


def format_sync_done_msg(
    trim_a: float,
    trim_b: float,
    common: float,
    out_a: Path,
    out_b: Path,
) -> str:
    return (
        f"对齐完成：裁掉 A 开头 {trim_a:.3f}s，裁掉 B 开头 {trim_b:.3f}s，"
        f"共同时长 {common:.3f}s\n输出：\n  {out_a}\n  {out_b}"
    )


def run_sync(
    va: Path,
    vb: Path,
    out_a: Path,
    out_b: Path,
    *,
    manual_offset: float | None,
    max_audio_seconds: float,
    crf: str,
    video_mode: str = "reencode",
    progress: ProgressSink | None = None,
) -> tuple[float, float, float]:
    prog = progress or NullProgress()
    p0, p1, p2, p3, p4 = PHASE_P0, PHASE_P1, PHASE_P2, PHASE_P3, PHASE_P4

    dur_src_a = get_duration_seconds(va)
    dur_src_b = get_duration_seconds(vb)

    tdir = Path(tempfile.mkdtemp(prefix="syncvid_"))
    try:
        wa, wb = tdir / "a.wav", tdir / "b.wav"

        for label, path, wav, rs, re, dur in (
            ("提取音频 A", va, wa, p0, p1, dur_src_a),
            ("提取音频 B", vb, wb, p1, p2, dur_src_b),
        ):
            prog.set_phase(label)
            extract_audio_wav(
                path,
                wav,
                progress=prog,
                range_start=rs,
                range_end=re,
                duration_sec=dur,
            )

        prog.set_phase("计算时间偏移")
        prog.set_overall(p2)

        # 1. 计算 A 和 B 之间的相对偏移量（对齐两台相机的动作）
        trim_a, trim_b = estimate_lag_seconds(
            wa, wb, max_seconds=max_audio_seconds
        )
        if manual_offset is not None:
            trim_b += float(manual_offset)


        # ======================================================
        # 修改后：直接获取蜂鸣器结束点（最后一帧）
        # ======================================================
        prog.set_phase("检测 3s 蜂鸣器结束点")
        
        # 注意：这里调用的是修改后的 endpoint 函数
        buzzer_end = find_buzzer_endpoint(wa, duration_threshold=2.5)
        
        # 直接使用结束点作为裁剪偏移
        trim_a += buzzer_end
        trim_b += buzzer_end
        
        print(f">>> 信号分析：定位到蜂鸣器结束于 A 视频 {buzzer_end:.3f}s 处。")
        # ======================================================

        dur_a = dur_src_a - trim_a
        dur_b = dur_src_b - trim_b
        common = min(dur_a, dur_b)
        
        if common <= 0:
            raise ValueError(
                f"裁剪后时长不足 ({common:.2f}s)，请检查蜂鸣器检测是否偏移过大或视频太短。"
            )
            
        prog.set_overall(p3)

        for label, src, dst, skip, rs, re in (
            ("编码输出 A", va, out_a, trim_a, p3, p4),
            ("编码输出 B", vb, out_b, trim_b, p4, 1.0),
        ):
            prog.set_phase(label)
            trim_and_encode(
                src,
                dst,
                skip_sec=skip,
                duration_sec=common,
                crf=crf,
                video_mode=video_mode,
                progress=prog,
                range_start=rs,
                range_end=re,
            )

        prog.set_phase("完成")
        prog.set_overall(1.0)
    finally:
        _cleanup_sync_temp(tdir)

    return trim_a, trim_b, common
# =============================================================================
# Tk GUI
# =============================================================================
def default_gui_output_paths(
    va: Path, vb: Path, out_dir_a: Path, out_dir_b: Path
) -> tuple[Path, Path]:
    oa = out_dir_a / f"{va.stem}_aligned.mp4"
    ob = out_dir_b / f"{vb.stem}_aligned.mp4"
    if oa.resolve() == ob.resolve():
        ob = out_dir_b / f"{vb.stem}_aligned_2.mp4"
    return oa, ob


def pick_inputs_gui() -> tuple[Path, Path, Path, Path] | None:
    from tkinter import Tk, filedialog, messagebox

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update_idletasks()

    video_types = [
        ("视频文件", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.wmv"),
        ("所有文件", "*.*"),
    ]
    p1 = filedialog.askopenfilename(
        parent=root,
        title="选择第一个视角视频",
        filetypes=video_types,
    )
    if not p1:
        root.destroy()
        return None
    p2 = filedialog.askopenfilename(
        parent=root,
        title="选择第二个视角视频",
        filetypes=video_types,
    )
    if not p2:
        root.destroy()
        return None

    va, vb = Path(p1).resolve(), Path(p2).resolve()
    if va == vb:
        messagebox.showerror("错误", "不能选择同一个文件作为两个视角。")
        root.destroy()
        return None

    root.destroy()

    dir_a = GUI_OUTPUT_DIR_FIRST.expanduser().resolve()
    dir_b = GUI_OUTPUT_DIR_SECOND.expanduser().resolve()
    dir_a.mkdir(parents=True, exist_ok=True)
    dir_b.mkdir(parents=True, exist_ok=True)

    out_a, out_b = default_gui_output_paths(va, vb, dir_a, dir_b)
    return va, vb, out_a, out_b


def _tk_message(title: str, text: str, *, error: bool = False) -> None:
    from tkinter import Tk
    from tkinter import messagebox

    r = Tk()
    r.withdraw()
    if error:
        messagebox.showerror(title, text)
    else:
        messagebox.showinfo(title, text)
    r.destroy()


def run_sync_gui_threaded(
    va: Path,
    vb: Path,
    out_a: Path,
    out_b: Path,
    args: argparse.Namespace,
) -> tuple[float, float, float] | None:
    from tkinter import Label, StringVar, Tk, ttk

    q: queue.Queue[tuple[str, object]] = queue.Queue()
    root = Tk()
    root.title("正在同步视频")
    root.resizable(False, False)
    status = StringVar(value="准备…")
    Label(root, textvariable=status, width=52, anchor="w").pack(
        padx=14, pady=(12, 6)
    )
    bar = ttk.Progressbar(root, length=460, mode="determinate", maximum=1000)
    bar.pack(padx=14, pady=(0, 14))

    sync_out: dict[str, object] = {}

    def worker() -> None:
        sink = QueueProgress(q)
        try:
            sync_out["ok"] = run_sync(
                va,
                vb,
                out_a,
                out_b,
                manual_offset=args.manual_offset,
                max_audio_seconds=args.max_audio_seconds,
                crf=args.crf,
                video_mode=getattr(args, "video_mode", "reencode"),
                progress=sink,
            )
        except BaseException as e:
            sync_out["err"] = e
        finally:
            q.put(("done", None))

    def poll() -> None:
        try:
            while True:
                kind, val = q.get_nowait()
                if kind == "phase":
                    status.set(str(val))
                elif kind == "overall":
                    bar["value"] = int(1000 * float(val))
                elif kind == "done":
                    root.quit()
                    return
        except queue.Empty:
            pass
        root.after(70, poll)

    threading.Thread(target=worker, daemon=True).start()
    root.after(60, poll)
    root.mainloop()
    root.destroy()

    err = sync_out.get("err")
    if err is not None:
        if isinstance(err, (ValueError, RuntimeError)):
            _tk_message("同步失败", str(err), error=True)
        else:
            _tk_message("同步失败", f"{type(err).__name__}: {err}", error=True)
        return None

    ok = sync_out.get("ok")
    if ok is None:
        return None
    return cast(tuple[float, float, float], ok)


# =============================================================================
# 抽帧（OpenCV）
# =============================================================================
def _write_image(path: Path, frame, im_ext: str, imwrite_params: list[int]) -> bool:
    """将帧写入磁盘；用 imencode + Path.write_bytes，兼容 Windows 中文路径。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(im_ext, frame, imwrite_params)
    if not ok or buf is None:
        return False
    try:
        path.write_bytes(buf.tobytes())
    except OSError:
        return False
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def extract_frames(
    left_video_path: str,
    right_video_path: str,
    output_dir: str,
    interval_frames: int = 30,
    start_frame: int = 0,
    max_pairs: int | None = None,
    progress_callback: Callable[[float, str], None] | None = None,
    *,
    image_format: str = "png",
    jpeg_quality: int = 100,
) -> int:
    """同步抽帧：同索引读左右帧；两路视频须已时间对齐。

    默认 ``image_format='png'`` 为无损保存（不引入 JPEG 块效应）；空间分辨率与解码帧一致。
    ``image_format='jpg'`` 时使用 ``jpeg_quality``（1–100，100 最高）。
    """
    cap_left = cv2.VideoCapture(left_video_path)
    cap_right = cv2.VideoCapture(right_video_path)

    if not cap_left.isOpened():
        print(f"错误：无法打开左视频文件 {left_video_path}")
        return 0
    if not cap_right.isOpened():
        print(f"错误：无法打开右视频文件 {right_video_path}")
        cap_left.release()
        return 0

    fps_left = cap_left.get(cv2.CAP_PROP_FPS)
    fps_right = cap_right.get(cv2.CAP_PROP_FPS)
    total_frames_left = int(cap_left.get(cv2.CAP_PROP_FRAME_COUNT))
    total_frames_right = int(cap_right.get(cv2.CAP_PROP_FRAME_COUNT))
    total_frames = max(1, min(total_frames_left, total_frames_right))
    w_l = int(cap_left.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_l = int(cap_left.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w_r = int(cap_right.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_r = int(cap_right.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fmt = (image_format or "png").strip().lower().lstrip(".")
    if fmt in ("jpeg",):
        fmt = "jpg"
    if fmt not in ("png", "jpg"):
        raise ValueError(f"image_format 须为 png 或 jpg，当前: {image_format!r}")
    jq = int(np.clip(int(jpeg_quality), 1, 100))
    im_ext = ".png" if fmt == "png" else ".jpg"
    imwrite_params = (
        [int(cv2.IMWRITE_PNG_COMPRESSION), 2]
        if fmt == "png"
        else [int(cv2.IMWRITE_JPEG_QUALITY), jq]
    )

    print(f"左视频: {fps_left:.2f} fps, 总帧数 {total_frames_left}, 解码分辨率 {w_l}x{h_l}")
    print(f"右视频: {fps_right:.2f} fps, 总帧数 {total_frames_right}, 解码分辨率 {w_r}x{h_r}")
    print(f"抽帧保存格式: {im_ext}（OpenCV 按视频原始分辨率写图，未做缩放）")

    if abs(fps_left - fps_right) > 0.1:
        print("警告：左右视频帧率不一致，可能导致不同步！")
    if total_frames_left != total_frames_right:
        print("警告：左右视频总帧数不同，请确认视频是否同步录制。")

    output_path = Path(output_dir)
    left_out_dir = output_path / "left"
    right_out_dir = output_path / "right"
    left_out_dir.mkdir(parents=True, exist_ok=True)
    right_out_dir.mkdir(parents=True, exist_ok=True)

    if progress_callback is not None:
        progress_callback(0.0, "正在抽帧")

    frame_idx = 0
    saved_count = 0
    attempted_writes = 0
    write_failures = 0

    while True:
        ret_left, frame_left = cap_left.read()
        ret_right, frame_right = cap_right.read()

        if not ret_left or not ret_right:
            print("视频读取完毕或出错")
            break

        if frame_idx >= start_frame and (frame_idx - start_frame) % interval_frames == 0:
            left_filename = f"left_{saved_count:06d}{im_ext}"
            right_filename = f"right_{saved_count:06d}{im_ext}"
            left_path = left_out_dir / left_filename
            right_path = right_out_dir / right_filename

            attempted_writes += 1
            ok_left = _write_image(left_path, frame_left, im_ext, imwrite_params)
            ok_right = _write_image(right_path, frame_right, im_ext, imwrite_params)
            if ok_left and ok_right:
                saved_count += 1
                if saved_count == 1 or (saved_count % 20 == 0):
                    print(f"已保存 {saved_count} 对图像")
                if max_pairs is not None and saved_count >= max_pairs:
                    print(f"已达到最大抽取对数 {max_pairs}，停止。")
                    frame_idx += 1
                    break
            else:
                write_failures += 1
                if not ok_left:
                    print(f"错误：无法写入左图 {left_path}")
                if not ok_right:
                    print(f"错误：无法写入右图 {right_path}")

        frame_idx += 1

        if frame_idx % 300 == 0:
            print(f"处理帧 {frame_idx} / {total_frames}")
        if progress_callback is not None and (frame_idx % 30 == 0 or frame_idx >= total_frames):
            progress_callback(min(1.0, frame_idx / total_frames), "正在抽帧")

    cap_left.release()
    cap_right.release()

    if progress_callback is not None:
        progress_callback(1.0, "抽帧完成")

    if saved_count == 0 and attempted_writes > 0:
        raise RuntimeError(
            f"抽帧写盘失败：尝试保存 {attempted_writes} 次，成功 0 对（失败 {write_failures} 次）。"
            f"输出目录：{output_path.resolve()}。"
            "请检查磁盘权限，或改用纯英文路径（如 D:\\video_sync_out）后重试。"
        )

    print(f"完成！共保存 {saved_count} 对图片到 {output_dir}")
    if write_failures > 0:
        print(f"警告：另有 {write_failures} 次写盘失败，实际成功对数少于采样次数。")
    return saved_count


#新增“蜂鸣器检测”函数
def find_buzzer_endpoint(wav_path: Path, duration_threshold: float = 2.5) -> float:
    """
    寻找持续响起的蜂鸣器结束点。
    :param duration_threshold: 蜂鸣器必须持续的最短秒数
    :return: 蜂鸣器结束的时间（秒），若未找到则返回 0.0
    """
    try:
        fs, data = load_wav_mono_float(wav_path)
        abs_data = np.abs(data)
        
        # 定义能量阈值：取全篇最大音量的 40%
        threshold = np.max(abs_data) * 0.4
        
        # 二值化处理
        is_loud = (abs_data > threshold).astype(np.float32)
        
        # 滑动窗口平滑（0.2秒步长）
        win_samples = int(0.2 * fs)
        if win_samples < 1: win_samples = 1
        kernel = np.ones(win_samples) / win_samples
        energy_density = np.convolve(is_loud, kernel, mode='same')
        
        # 寻找能量密度持续处于高位的索引
        loud_indices = np.where(energy_density > 0.7)[0]
        if len(loud_indices) < 2:
            return 0.0

        min_contig_samples = int(duration_threshold * fs)
        start_idx = loud_indices[0]
        
        for i in range(1, len(loud_indices)):
            # 检查是否发生中断（中断超过 0.2s 视为一段信号结束）
            if loud_indices[i] - loud_indices[i-1] > fs * 0.2:
                # 检查刚结束的这一段长度是否达标
                if (loud_indices[i-1] - start_idx) >= min_contig_samples:
                    # 返回上一段的结束点
                    return float(loud_indices[i-1] / fs)
                # 否则重置起点，继续找下一段
                start_idx = loud_indices[i]
            
            # 如果这一段一直持续，且已经超过了阈值，但我们想找“最后一帧”
            # 所以这里不直接 return，而是让循环继续运行，直到遇到中断或数组结束
        
        # 检查最后一段是否满足条件
        if (loud_indices[-1] - start_idx) >= min_contig_samples:
            return float(loud_indices[-1] / fs)

        return 0.0
    except Exception as e:
        print(f"蜂鸣器结束点检测出错: {e}")
        return 0.0