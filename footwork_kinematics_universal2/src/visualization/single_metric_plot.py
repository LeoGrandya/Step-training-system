from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import pandas as pd

from src.outputs.label_maps import get_display_name, sanitize_filename


def _set_chinese_font():
    font_candidates = [
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    family = None
    for path in font_candidates:
        if Path(path).exists():
            try:
                fm.fontManager.addfont(path)
            except Exception:
                pass
            try:
                family = fm.FontProperties(fname=path).get_name()
                break
            except Exception:
                pass
    if family is None:
        family = "DejaVu Sans"
    plt.rcParams["font.family"] = [family, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def plot_single_metrics(df: pd.DataFrame, metric_names, out_dir, x_col="time_s"):
    _set_chinese_font()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    x_label = get_display_name(x_col)

    for metric in metric_names:
        if metric not in df.columns:
            continue

        sub = df[[x_col, metric]].dropna()
        if sub.empty:
            continue

        metric_label = get_display_name(metric)
        file_name = sanitize_filename(metric) + ".png"

        plt.figure(figsize=(10, 4.5))
        plt.plot(sub[x_col], sub[metric])
        plt.xlabel(x_label)
        plt.ylabel(metric_label)
        plt.title(f"{metric_label}变化曲线")
        plt.grid(alpha=0.25)
        plt.tight_layout()
        plt.savefig(out_dir / file_name, dpi=150)
        plt.close()
