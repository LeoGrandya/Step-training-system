from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pandas as pd

from src.outputs.label_maps import FILE_DESCRIPTION_MAP, rename_columns_for_display


def _ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def write_display_csv(df: pd.DataFrame, out_path):
    out_path = Path(out_path)
    _ensure_parent(out_path)
    display_df = rename_columns_for_display(df.copy())
    display_df.to_csv(out_path, index=False, encoding="utf-8-sig")


def write_display_excel(df: pd.DataFrame, out_path, sheet_name: str):
    out_path = Path(out_path)
    _ensure_parent(out_path)
    display_df = rename_columns_for_display(df.copy())
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        display_df.to_excel(writer, index=False, sheet_name=sheet_name)
        ws = writer.book[sheet_name]
        ws.freeze_panes = "A2"
        for col in ws.columns:
            max_len = 0
            letter = col[0].column_letter
            for cell in col:
                value = "" if cell.value is None else str(cell.value)
                max_len = max(max_len, len(value))
            ws.column_dimensions[letter].width = min(max(max_len + 2, 10), 36)


def write_summary_json(df: pd.DataFrame, out_path):
    out_path = Path(out_path)
    _ensure_parent(out_path)
    if df is None or df.empty:
        payload = {}
    else:
        display_df = rename_columns_for_display(df.copy())
        record = display_df.iloc[0].to_dict()
        payload = {k: (None if pd.isna(v) else v) for k, v in record.items()}
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_output_manifest(out_dir, files: Dict[str, str]):
    out_dir = Path(out_dir)
    payload = {
        "输出目录": str(out_dir),
        "输出文件说明": [],
    }
    for rel_path, desc in files.items():
        payload["输出文件说明"].append({
            "文件": rel_path,
            "说明": desc,
        })
    # append standard descriptions when not already present
    existing = {item["文件"] for item in payload["输出文件说明"]}
    for rel_path, desc in FILE_DESCRIPTION_MAP.items():
        if rel_path not in existing:
            payload["输出文件说明"].append({"文件": rel_path, "说明": desc})
    path = out_dir / "00_输出清单.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
