"""按彩种对本地 CSV 做多源/回访校验。"""

from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from newam6hc_lib import (
    BASE_168,
    BASE_55128,
    KINDS,
    MACAU6HC_168,
    NEW_AM6HC,
    fetch_168_history,
    fetch_55128_detail,
    fetch_55128_year,
    load_csv,
    row_balls,
    rows_to_verified_csv_dict,
    save_verified_csv,
)


def compare_maps(local: dict[int, list[int]], remote: dict[int, list[int]], label: str) -> dict:
    shared = set(local) & set(remote)
    mismatches = [
        {"issue": i, "local": local[i], "remote": remote[i]}
        for i in sorted(shared)
        if local[i] != remote[i]
    ]
    return {
        "source": label,
        "shared_issues": len(shared),
        "only_local": len(set(local) - set(remote)),
        "only_remote": len(set(remote) - set(local)),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:50],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="校验六合彩 CSV")
    parser.add_argument("--kind", choices=list(KINDS.keys()), required=True)
    parser.add_argument("--csv", type=Path, default=None)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data",
    )
    parser.add_argument("--years", type=int, nargs="+", default=[2022, 2023, 2024, 2025, 2026])
    parser.add_argument("--detail-sample", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args()

    kind = KINDS[args.kind]
    default_csv = {
        "newam6hc": "newam6hc_5y.csv",
        "am6hc": "am6hc_5y.csv",
        "macau6hc_168": "macau6hc_168.csv",
    }[kind.key]
    csv_path = args.csv or (args.out_dir / default_csv)
    if not csv_path.is_file():
        raise SystemExit(f"找不到 {csv_path}，请先运行 fetch_marksix.py --kind {kind.key}")

    csv_rows = load_csv(csv_path)
    local = {issue: row_balls(row) for issue, row in csv_rows.items()}

    live_55128: dict[int, list[int]] = {}
    compare_55128 = None
    compare_168 = None
    detail_report = {"sample_size": 0, "mismatch_count": 0, "mismatches": []}

    if kind.api_name_55128:
        print("重新抓取 55128 年页...")
        for year in args.years:
            for row in fetch_55128_year(kind, year):
                live_55128[row["issue"]] = row["nums"] + [row["special"]]
            if args.delay:
                time.sleep(args.delay)
        compare_55128 = compare_maps(local, live_55128, "55128_live_year_pages")

        rng = random.Random(args.seed)
        sample = sorted(rng.sample(sorted(local.keys()), min(args.detail_sample, len(local))))
        bad = 0
        for issue in sample:
            web = fetch_55128_detail(kind, issue)
            if local[issue] != web:
                bad += 1
                detail_report["mismatches"].append(
                    {"issue": issue, "local": local[issue], "detail_page": web}
                )
            if args.delay:
                time.sleep(args.delay)
        detail_report = {
            "sample_size": len(sample),
            "mismatch_count": bad,
            "issues_sampled": sample,
            "mismatches": detail_report["mismatches"],
        }

    remote_168: dict[int, list[int]] = {}
    if kind.game_168:
        print("重新抓取 168 全部分页...")
        for row in fetch_168_history(kind):
            remote_168[row["issue"]] = row["nums"] + [row["special"]]
        compare_168 = compare_maps(local, remote_168, f"168yh_game_{kind.game_168}")

    ok_55128 = {i for i in local if i in live_55128 and local[i] == live_55128[i]}
    ok_168 = {i for i in local if i in remote_168 and local[i] == remote_168[i]}

    if kind is MACAU6HC_168:
        print("168 专用数据集：仅与 168 回访比对。")

    verified = []
    for issue in sorted(local.keys(), reverse=True):
        row = csv_rows[issue]
        sources = []
        if issue in ok_55128:
            sources.append("55128")
        if issue in ok_168:
            sources.append("168yh_refetch" if kind is MACAU6HC_168 else "168yh")
        if kind.api_name_55128 and kind.game_168 and issue in ok_55128 and issue in ok_168:
            status = "dual_verified"
        elif kind is MACAU6HC_168 and issue in ok_168:
            status = "verified"
        elif kind.api_name_55128 and issue in ok_55128:
            status = "verified"
        else:
            status = "failed"
        vrow = rows_to_verified_csv_dict(
            {
                "issue": issue,
                "year": int(row["year"]),
                "seq": int(row["seq"]),
                "lottery": kind.key,
                "nums": local[issue][:6],
                "special": local[issue][6],
                "colors": row.get("colors", "").split(",") if row.get("colors") else [],
                "zodiacs": row.get("zodiacs", "").split(",") if row.get("zodiacs") else [],
                "wuxings": row.get("wuxings", "").split(",") if row.get("wuxings") else [],
                "open_time": row.get("open_time", ""),
            },
            status,
            "+".join(sources),
        )
        verified.append(vrow)

    verified = [r for r in verified if r["verify_status"] != "failed"]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "kind": kind.key,
        "display_name": kind.display_name,
        "input_csv": str(csv_path),
        "total_issues": len(local),
        "compare_55128": compare_55128,
        "compare_168": compare_168,
        "detail_page_spot_check": detail_report,
        "summary": {
            "verified_rows": len(verified),
            "failed": len(local) - len(verified),
            "dual_with_168": len(ok_55128 & ok_168) if kind.game_168 and kind.api_name_55128 else 0,
        },
        "note": (
            "am6hc(55128澳门彩) 与 macau6hc_168(168澳门六合彩) 为不同产品线，"
            "同期号号码不应相同；勿合并到同一训练集。"
        ),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = default_csv.replace(".csv", "")
    report_path = args.out_dir / f"verification_{kind.key}.json"
    verified_path = args.out_dir / f"{stem}_verified.csv"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    save_verified_csv(verified, verified_path)

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"报告: {report_path}")
    print(f"数据集: {verified_path}")

    if kind is not MACAU6HC_168 and compare_55128 and compare_55128["mismatch_count"]:
        raise SystemExit(1)
    if kind is MACAU6HC_168 and compare_168 and compare_168["mismatch_count"]:
        raise SystemExit(1)
    elif compare_168 and compare_168["mismatch_count"]:
        raise SystemExit(2)
    if detail_report.get("mismatch_count"):
        raise SystemExit(3)


if __name__ == "__main__":
    main()
