"""从 55128 抓取新澳门彩（兼容入口，请优先使用 fetch_marksix.py）。"""

import subprocess
import sys


def main() -> None:
    cmd = [sys.executable, "fetch_marksix.py", "--kind", "newam6hc", *sys.argv[1:]]
    raise SystemExit(subprocess.call(cmd, cwd=__import__("pathlib").Path(__file__).resolve().parent))


if __name__ == "__main__":
    main()
