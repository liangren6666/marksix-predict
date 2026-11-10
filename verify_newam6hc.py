"""校验新澳门彩（兼容入口）。"""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    cmd = [sys.executable, str(root / "verify_marksix.py"), "--kind", "newam6hc", *sys.argv[1:]]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
