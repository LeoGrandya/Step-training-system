"""一次性迁移：8 个字段英文值 → 中文值。幂等（只改英文值，中文值不动）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.db import db, init_database
from flask import Flask

MIGRATIONS = [
    ("subjects", "hand", [("right", "右手"), ("left", "左手")]),
    ("subjects", "level", [("amateur", "业余"), ("level-2", "二级"), ("level-1", "一级")]),
    ("accounts", "status", [("active", "启用"), ("disabled", "禁用")]),
    ("training_videos", "status", [("uploaded", "已上传"), ("processing", "处理中"), ("done", "已完成"), ("failed", "失败")]),
    ("training_configs", "mode", [("eval", "练习评估"), ("free", "自由练习"), ("test", "能力测试")]),
    ("training_configs", "analysis_profile", [("fast", "快速"), ("balanced", "均衡"), ("quality", "高质量")]),
    ("evaluation_records", "grade", [("excellent", "优秀"), ("good", "良好"), ("pass", "合格"), ("needs_work", "待提高")]),
    ("footwork_types", "category", [("basic", "基础步伐"), ("pattern", "步法模式")]),
]


def run():
    app = Flask(__name__)
    init_database(app)
    app.app_context().push()

    changed = 0
    for table, column, pairs in MIGRATIONS:
        for old_val, new_val in pairs:
            result = db.session.execute(
                db.text(f"UPDATE {table} SET {column} = :new WHERE {column} = :old"),
                {"new": new_val, "old": old_val},
            )
            n = result.rowcount
            if n:
                print(f"  {table}.{column}: '{old_val}' → '{new_val}' ({n} rows)")
                changed += n
    db.session.commit()
    print(f"\nDone. {changed} rows updated.")
    return changed


if __name__ == "__main__":
    run()
