"""把新澳门彩最新开奖合并进已校验数据。没有新期号时不改文件。"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from newam6hc_lib import (
    NEW_AM6HC,
    fetch_55128_year,
    load_csv,
    rows_to_verified_csv_dict,
    save_csv,
    save_verified_csv,
)

VERIFIED = ROOT / "data" / "newam6hc_5y_verified.csv"
PLAIN = ROOT / "data" / "newam6hc_5y.csv"


def _balls(row: dict) -> list[int]:
    return [int(row[f"n{i}"]) for i in range(1, 7)] + [int(row["special"])]


def _verified_from_draw(row: dict) -> dict:
    return rows_to_verified_csv_dict(row, "verified", "55128")


def _plain_from_verified(row: dict) -> dict:
    return {
        "issue": int(row["issue"]),
        "year": int(row["year"]),
        "seq": int(row["seq"]),
        "lottery": row.get("lottery") or "newam6hc",
        "nums": [int(row[f"n{i}"]) for i in range(1, 7)],
        "special": int(row["special"]),
        "colors": [part for part in str(row.get("colors") or "").split(",") if part],
        "zodiacs": [part for part in str(row.get("zodiacs") or "").split(",") if part],
        "wuxings": [part for part in str(row.get("wuxings") or "").split(",") if part],
        "open_time": row.get("open_time") or "",
    }


def main() -> None:
    existing = load_csv(VERIFIED)
    if not existing:
        raise SystemExit(f"没有现成数据: {VERIFIED}")
    latest_before = max(existing)
    this_year = date.today().year
    years = sorted({this_year, this_year - 1, int(str(latest_before)[:4])})
    fresh: dict[int, dict] = {}
    for year in years:
        rows = fetch_55128_year(NEW_AM6HC, year)
        print(f"{year} 年抓到 {len(rows)} 期")
        if year == this_year and not rows:
            raise SystemExit(f"{year} 年没有抓到开奖，已保留原文件")
        for row in rows:
            fresh[int(row["issue"])] = row

    changed = False
    for issue, row in fresh.items():
        balls = row["nums"] + [row["special"]]
        if issue not in existing or _balls(existing[issue]) != balls:
            changed = True
            existing[issue] = _verified_from_draw(row)

    latest_after = max(existing)
    print(f"更新前最新期号 {latest_before}，现在 {latest_after}，changed={changed}")
    if changed:
        ordered = [existing[issue] for issue in sorted(existing, reverse=True)]
        save_verified_csv(ordered, VERIFIED)
        save_csv([_plain_from_verified(row) for row in ordered], PLAIN)

    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"changed={'true' if changed else 'false'}\n")
            handle.write(f"latest={latest_after}\n")


if __name__ == "__main__":
    main()
