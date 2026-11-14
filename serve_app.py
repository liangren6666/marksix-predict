"""解压后双击启动的桌面程序。"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ROOT = app_root()
os.environ.setdefault("LOTTERY_ROOT", str(ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SEEDED = (
    "data/newam6hc_5y_verified.csv",
    "data/newam6hc_5y.csv",
    "data/am6hc_5y_verified.csv",
    "data/am6hc_5y.csv",
    "data/macau6hc_168_verified.csv",
    "data/macau6hc_168.csv",
    "data/model_benchmark.json",
    "data/model_benchmark.csv",
    "data/forecasts.json",
    "data/regular_benchmark.json",
    "data/train_report.json",
    "data/next_reference.json",
    "data/prediction_reference.json",
    "models/hgb_special.pkl",
    "models/logreg_special.pkl",
)


def seed_runtime_files() -> None:
    """第一次打开时，把随包携带的数据和模型复制到程序旁边，之后的更新写在这里。"""
    bundled = Path(getattr(sys, "_MEIPASS", ""))
    if not bundled.is_dir():
        return
    for relative in SEEDED:
        dest = ROOT / relative
        src = bundled / relative
        if dest.exists() or not src.is_file():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


seed_runtime_files()

from desktop_server import open_window


def self_check() -> int:
    from ml.data import load_newam6hc
    from ml.next_reference import DEFAULT_MODEL_DIR
    from ml.web_prediction import _load_special_pack

    frame = load_newam6hc()
    _load_special_pack(DEFAULT_MODEL_DIR)
    print(f"ok draws={len(frame)} latest={int(frame.issue.iloc[-1])}")
    return 0


def main() -> None:
    if "--self-check" in sys.argv:
        raise SystemExit(self_check())
    open_window()


if __name__ == "__main__":
    main()
