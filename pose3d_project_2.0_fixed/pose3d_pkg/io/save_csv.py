import csv
from pathlib import Path
from typing import Iterable


def ensure_parent(path: str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_csv_rows(path: str, header: list[str], rows: Iterable[list]):
    p = ensure_parent(path)
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
