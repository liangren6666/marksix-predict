"""
新澳门彩（特码）预测可行性实验：
时间顺序划分 + 深度学习 vs 统计基线 vs 随机理论值。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ml.baselines import frequency_top1, markov_order1
from ml.data import (
    DEFAULT_CSV,
    build_multihot_windows,
    build_special_windows,
    load_newam6hc,
    temporal_split_index,
)
from ml.train_special import train_lstm, train_mlp

RANDOM_TOP1 = 1.0 / 49
RANDOM_TOP3 = 3.0 / 49
RANDOM_TOP5 = 5.0 / 49


def _repeat_last_full(specials: np.ndarray, test_start: int, test_len: int) -> dict:
    """策略：下一期特码 = 上一期特码。"""
    if test_len <= 0:
        return {"name": "repeat_last", "top1_acc": 0.0}
    hits = sum(
        1
        for j in range(test_len)
        if specials[test_start + j] == specials[test_start + j - 1]
    )
    return {"name": "repeat_last", "top1_acc": hits / test_len}


def permutation_test_specials(specials: np.ndarray, n_perm: int = 200) -> dict:
    """破坏时间顺序后，一阶马尔可夫应接近随机。"""
    rng = np.random.default_rng(0)
    accs = []
    for _ in range(n_perm):
        shuffled = rng.permutation(specials)
        split = int(len(shuffled) * 0.85)
        m = markov_order1(shuffled[:split], shuffled[split:])
        accs.append(m["top1_acc"])
    return {
        "mean_top1": float(np.mean(accs)),
        "std_top1": float(np.std(accs)),
        "n_perm": n_perm,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--window", type=int, default=30)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "feasibility_report.json")
    parser.add_argument("--quick", action="store_true", help="缩短训练轮数")
    args = parser.parse_args()

    df = load_newam6hc(args.csv)
    specials = df["special"].to_numpy()
    draws = df[[f"n{i}" for i in range(1, 7)] + ["special"]].to_numpy()

    x_seq, y = build_special_windows(specials, args.window)
    x_mlp, _ = build_multihot_windows(draws, args.window)

    n = len(y)
    train_end, val_end = temporal_split_index(n, 0.7, 0.15)
    slices = {
        "train": (slice(0, train_end), slice(0, train_end)),
        "val": (slice(train_end, val_end), slice(train_end, val_end)),
        "test": (slice(val_end, n), slice(val_end, n)),
    }

    train_s = specials[args.window : args.window + train_end]
    test_s = specials[args.window + val_end :]

    baselines = {
        "random_theory": {
            "top1": RANDOM_TOP1,
            "top3": RANDOM_TOP3,
            "top5": RANDOM_TOP5,
        },
        "frequency_top1": frequency_top1(train_s, test_s),
        "markov_order1": markov_order1(train_s, test_s),
        "repeat_last": _repeat_last_full(specials, args.window + val_end, len(test_s)),
    }

    epochs_lstm = 25 if args.quick else 45
    epochs_mlp = 30 if args.quick else 60

    lstm_val = train_lstm(
        x_seq[:train_end],
        y[:train_end],
        x_seq[train_end:val_end],
        y[train_end:val_end],
        epochs=epochs_lstm,
    )
    lstm_test = train_lstm(
        x_seq[:val_end],
        y[:val_end],
        x_seq[val_end:],
        y[val_end:],
        epochs=epochs_lstm,
    )

    mlp_val = train_mlp(
        x_mlp[:train_end],
        y[:train_end],
        x_mlp[train_end:val_end],
        y[train_end:val_end],
        epochs=epochs_mlp,
    )
    mlp_test = train_mlp(
        x_mlp[:val_end],
        y[:val_end],
        x_mlp[val_end:],
        y[val_end:],
        epochs=epochs_mlp,
    )

    perm = permutation_test_specials(specials, n_perm=100 if args.quick else 200)

    def verdict(model_top1: float, baseline_top1: float) -> str:
        margin = model_top1 - RANDOM_TOP1
        if model_top1 <= RANDOM_TOP1 + 0.002:
            return "no_edge"
        if model_top1 <= baseline_top1:
            return "below_simple_baseline"
        if margin < 0.01:
            return "marginal_unstable"
        return "needs_more_oos_validation"

    report = {
        "dataset": str(args.csv),
        "target": "next_special_number",
        "n_draws": int(len(df)),
        "issue_range": [int(df.issue.iloc[0]), int(df.issue.iloc[-1])],
        "window": args.window,
        "split": {
            "train_samples": train_end,
            "val_samples": val_end - train_end,
            "test_samples": n - val_end,
        },
        "random_baseline": baselines["random_theory"],
        "statistical_baselines_on_test": {
            k: baselines[k] for k in ("frequency_top1", "markov_order1", "repeat_last")
        },
        "lstm": {
            "val": lstm_val.__dict__,
            "test": lstm_test.__dict__,
            "verdict_test": verdict(lstm_test.top1_acc, baselines["markov_order1"]["top1_acc"]),
        },
        "mlp_multihot": {
            "val": mlp_val.__dict__,
            "test": mlp_test.__dict__,
            "verdict_test": verdict(mlp_test.top1_acc, baselines["markov_order1"]["top1_acc"]),
        },
        "permutation_null_markov": perm,
        "interpretation_zh": {
            "目标说明": "用过去 window 期信息预测下一期特码（49 类分类）",
            "理论随机Top1": f"{RANDOM_TOP1:.4f}（约 2.04%）",
            "若无法稳定超过随机+1%且超过马尔可夫基线": "历史数据未呈现可交易的预测优势",
            "深度学习风险": "易在训练集过拟合伪规律；必须以时间外测试集为准",
            "数据局限": "第三方开奖聚合数据，不保证等同官方物理开奖过程",
            "合规与用途": "研究用途；勿视为投资建议或必胜策略",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n已写入: {args.out}")


if __name__ == "__main__":
    main()
