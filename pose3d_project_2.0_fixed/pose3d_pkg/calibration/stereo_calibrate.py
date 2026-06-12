"""双目参数处理。
当前版本重点支持两种来源：
1. 直接读取 stereo_params.json
2. 从 user_params.py 中的 manual_stereo_params 写出 stereo_params.json
"""

import json
from pathlib import Path
from typing import Dict


def write_stereo_params_json(manual_params: Dict, save_path: str) -> str:
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(manual_params, f, indent=2, ensure_ascii=False)
    return str(save_path)


def load_stereo_params_json(json_path: str) -> Dict:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def prepare_stereo_params(settings: Dict, json_path: str | None = None) -> str:
    stereo_cfg = settings["stereo"]
    mode = stereo_cfg["stereo_mode"].lower()
    if json_path is None:
        json_path = stereo_cfg["stereo_params_json"]

    if mode == "json":
        return json_path
    if mode == "manual":
        manual_params = stereo_cfg["manual_stereo_params"]
        return write_stereo_params_json(manual_params, json_path)
    raise ValueError(f"不支持的 stereo_mode: {mode}")
