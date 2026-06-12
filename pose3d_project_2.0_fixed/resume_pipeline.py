"""
断点续跑脚本 —— 不修改任何现有代码。

用法：
    python resume_pipeline.py

逻辑：
    1. 加载 user_params.py 配置
    2. 遍历所有 stereo pair
    3. 如果输出目录下已有 pose3d_abs.csv → 跳过
    4. 否则 → 处理该 pair
"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pose3d_pkg.cli.run_pipeline import (
    load_settings_from_py,
    discover_stereo_pairs,
    build_pair_output_paths,
    process_one_pair,
    _pre_calibrate_all_groups,
)
from pose3d_pkg.calibration.stereo_calibrate import prepare_stereo_params


def main():
    config_path = str(PROJECT_ROOT / "pose3d_pkg" / "user_params.py")
    settings = load_settings_from_py(config_path)

    all_pairs = discover_stereo_pairs(settings)
    print(f"\n共检测到 {len(all_pairs)} 对双目视频。\n", flush=True)

    # 分类：已完成 / 待处理
    completed = []
    pending = []

    for pair_info in all_pairs:
        pair_paths = build_pair_output_paths(settings, pair_info)
        abs_csv_path = Path(pair_paths["pose3d_abs_csv"])

        if abs_csv_path.exists():
            completed.append(pair_info)
        else:
            pending.append(pair_info)

    print(f"已完成: {len(completed)} 对", flush=True)
    for p in completed:
        print(f"  [跳过] {p['pair_name']}", flush=True)

    print(f"\n待处理: {len(pending)} 对", flush=True)
    for p in pending:
        print(f"  [待处理] {p['pair_name']}", flush=True)

    if not pending:
        print("\n全部已完成，无需处理。", flush=True)
        return {}

    # 预标定地面控制点（已标定的 group 会自动跳过）
    _pre_calibrate_all_groups(settings, all_pairs)

    # 逐对处理待处理的 pair
    pair_timings = {}
    for i, pair_info in enumerate(pending, 1):
        print(f"\n{'='*60}", flush=True)
        print(f"进度: {i}/{len(pending)}", flush=True)
        print(f"{'='*60}", flush=True)

        stereo_params_json = prepare_stereo_params(
            settings, pair_info["stereo_params_json"]
        )
        pair_timings[pair_info["pair_name"]] = process_one_pair(
            settings=settings,
            stereo_params_json=stereo_params_json,
            pair_info=pair_info,
        )

    print("\n" + "=" * 60, flush=True)
    print("断点续跑完成。", flush=True)
    print(f"本次处理: {len(pending)} 对", flush=True)
    print(f"跳过(已完成): {len(completed)} 对", flush=True)
    return pair_timings


if __name__ == "__main__":
    main()
