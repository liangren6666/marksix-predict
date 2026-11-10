"""用已训练模型对最新一期之后给出 Top-K 特码候选。"""

from __future__ import annotations

import argparse
from pathlib import Path

from ml.next_reference import build_next_reference


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "models",
    )
    parser.add_argument("--topk", type=int, default=10)
    args = parser.parse_args()

    ref = build_next_reference(model_dir=args.model_dir, topk=args.topk)
    last_issue = ref["last_draw"]["issue"]
    picks = ref["models"]["hgb_ensemble"]["picks"]

    print(f"基于期号 {last_issue} 之后，下一期特码 Top-{args.topk}（研究输出，非保证）：")
    for row in picks:
        print(f"  {row['rank']:2d}. {row['num']:02d}  P={row['p']:.4f}")


if __name__ == "__main__":
    main()
