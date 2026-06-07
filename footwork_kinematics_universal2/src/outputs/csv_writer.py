from pathlib import Path
import pandas as pd


def write_csv(df: pd.DataFrame, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
