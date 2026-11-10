"""解压后双击启动的桌面程序。"""

from __future__ import annotations

import os
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

from desktop_app import run


def main() -> None:
    run()


if __name__ == "__main__":
    main()
