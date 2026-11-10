"""写出 data/next_reference.json，供网站加载。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.next_reference import DEFAULT_OUT, write_next_reference


def main() -> None:
    parser = argparse.ArgumentParser(description="导出下一期特码参考 JSON")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
    )
    parser.add_argument("--topk", type=int, default=10)
    args = parser.parse_args()

    payload = write_next_reference(out=args.out, topk=args.topk)
    hgb = payload["models"]["hgb_ensemble"]
    print(json.dumps(
        {
            "out": str(args.out.resolve()),
            "last_issue": payload["last_draw"]["issue"],
            "next_issue_hint": payload["next_issue_hint"],
            "hgb_top1": hgb["top1"],
            "markov_top1": payload["models"]["markov_order1"]["top1"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    print(f"\n已写入: {args.out}")


if __name__ == "__main__":
    main()
