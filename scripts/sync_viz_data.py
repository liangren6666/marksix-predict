"""把网页使用的数据文件同步到 web/public/data。"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data"
DST = ROOT / "web" / "public" / "data"
FILES = [
    "newam6hc_5y_verified.csv",
    "am6hc_5y_verified.csv",
    "macau6hc_168_verified.csv",
    "newam6hc_5y.csv",
    "am6hc_5y.csv",
    "macau6hc_168.csv",
    "model_benchmark.csv",
    "model_benchmark.json",
    "train_report.json",
    "next_reference.json",
    "prediction_reference.json",
    "forecasts.json",
    "regular_benchmark.json",
]

DST.mkdir(parents=True, exist_ok=True)
for name in FILES:
    src = SRC / name
    if src.is_file():
        shutil.copy2(src, DST / name)
        print("copied", name)
