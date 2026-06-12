from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import pandas as pd

from src.outputs.label_maps import get_display_name


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


def plot_overview(df: pd.DataFrame, metric_names, out_path, x_col="time_s", title="总览"):
    _set_chinese_font()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    valid_metrics = [m for m in metric_names if m in df.columns]
    valid_metrics = [m for m in valid_metrics if not df[[x_col, m]].dropna().empty]

    if not valid_metrics:
        return

    fig, axes = plt.subplots(len(valid_metrics), 1, figsize=(12, max(3.6 * len(valid_metrics), 4.5)))
    if len(valid_metrics) == 1:
        axes = [axes]

    x_label = get_display_name(x_col)

    for ax, metric in zip(axes, valid_metrics):
        sub = df[[x_col, metric]].dropna()
        metric_label = get_display_name(metric)
        ax.plot(sub[x_col], sub[metric])
        ax.set_title(metric_label)
        ax.set_xlabel(x_label)
        ax.set_ylabel(metric_label)
        ax.grid(alpha=0.25)

    fig.suptitle(title, fontsize=14)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
