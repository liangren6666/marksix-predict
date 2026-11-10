"""抓取六合彩类彩种历史数据（55128 或 168）。"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from newam6hc_lib import (
    AM6HC,
    KINDS,
    MACAU6HC_168,
    NEW_AM6HC,
    fetch_168_history,
    fetch_55128_year,
    fetch_55128_years,
    save_csv,
)


def dedupe_rows(rows: list[dict]) -> list[dict]:
    seen: set[int] = set()
    out: list[dict] = []
    for r in sorted(rows, key=lambda x: x["issue"], reverse=True):
        if r["issue"] in seen:
            continue
        seen.add(r["issue"])
        out.append(r)
    return out


def fetch_55128_kind(kind, years: list[int], delay: float) -> list[dict]:
    all_rows: list[dict] = []
    for year in years:
        print(f"[{kind.display_name}] 抓取 {year} 年...")
        all_rows.extend(fetch_55128_year(kind, year))
        print(f"  -> 当年 {len(all_rows)} 期累计")
        if delay > 0:
            time.sleep(delay)
    return dedupe_rows(all_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="抓取六合彩历史")
    parser.add_argument(
        "--kind",
        choices=list(KINDS.keys()),
        required=True,
        help="newam6hc=新澳门彩(55128); am6hc=澳门彩(55128); macau6hc_168=澳门六合彩(168)",
    )
    parser.add_argument("--years", type=int, nargs="+", help="55128 按年抓取的年份列表")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data",
    )
    parser.add_argument("--delay", type=float, default=0.4)
    args = parser.parse_args()

    kind = KINDS[args.kind]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if kind is MACAU6HC_168:
        rows = fetch_168_history(kind)
        print(f"[{kind.display_name}] 168 共 {len(rows)} 期")
        stem = "macau6hc_168"
    else:
        if args.years:
            years = sorted(args.years)
        else:
            available = fetch_55128_years(kind)
            years = sorted(available)[-5:]
            print(f"可用年份: {available}")
            print(f"默认近五年: {years}")
        rows = fetch_55128_kind(kind, years, args.delay)
        stem = f"{kind.key}_5y"

    json_path = args.out_dir / f"{stem}.json"
    csv_path = args.out_dir / f"{stem}.csv"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    save_csv(rows, csv_path)

    issues = [r["issue"] for r in rows]
    print(f"\n彩票: {kind.display_name} ({kind.key})")
    print(f"合计 {len(rows)} 期")
    if issues:
        print(f"期号范围: {min(issues)} ~ {max(issues)}")
    print(f"已保存: {csv_path}")
    print(f"已保存: {json_path}")


if __name__ == "__main__":
    main()
