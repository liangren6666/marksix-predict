"""
三模型对比（新澳门彩特码）：理论随机 vs 马尔可夫 vs 梯度提升(HGB)
测试集封存，输出供网站展示。
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from sklearn.ensemble import HistGradientBoostingClassifier

from ml.benchmark_baselines import (
    markov_online_proba,
    prev_specials_for_split,
)
from ml.data import DEFAULT_CSV, load_newam6hc, temporal_split_index
from ml.evaluate import metrics_dict
from ml.features import build_feature_matrix
from ml.probability import predict_proba_49

RANDOM_TOP1 = 1 / 49

CORE_MODELS = [
    {
        "id": "random",
        "model": "理论随机",
        "kind": "baseline",
        "desc": "每期特码 1/49 均匀假设，不可学习时的底线（约 2.04% Top-1）。",
    },
    {
        "id": "markov",
        "model": "马尔可夫链",
        "kind": "baseline",
        "desc": "根据上一期特码查转移概率；简单规则中最常见、可解释的对照。",
    },
    {
        "id": "hgb",
        "model": "梯度提升(HGB)",
        "kind": "ml",
        "desc": "遗漏 + 窗口频次等表格特征；本数据集上较稳的机器学习方案。",
    },
]


def fit_hgb(x_tr, y_tr):
    return HistGradientBoostingClassifier(
        max_depth=6,
        max_iter=220,
        learning_rate=0.06,
        l2_regularization=1.2,
        min_samples_leaf=45,
        early_stopping=True,
        validation_fraction=0.12,
        n_iter_no_change=12,
        random_state=42,
    ).fit(x_tr, y_tr)


def row_entry(meta: dict, split: str, m: dict, seconds: float) -> dict:
    return {
        "id": meta["id"],
        "model": meta["model"],
        "kind": meta["kind"],
        "desc": meta["desc"],
        "split": split,
        "seconds": round(seconds, 3),
        "top1": round(m["top1"], 6),
        "top3": round(m["top3"], 6),
        "top5": round(m["top5"], 6),
        "top10": round(m["top10"], 6),
        "n": m["n"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--window", type=int, default=30)
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "model_benchmark.json",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "model_benchmark.csv",
    )
    args = parser.parse_args()

    df = load_newam6hc(args.csv)
    specials = df["special"].to_numpy()
    draws = df[[f"n{i}" for i in range(1, 7)] + ["special"]].to_numpy()

    x_tab, y = build_feature_matrix(specials, draws, args.window)
    n = len(y)
    train_end, val_end = temporal_split_index(n, 0.7, 0.15)
    test_len = n - val_end

    results: list[dict] = []

    # 理论期望为 k/49，不把某次随机模拟的波动当作理论值。
    for split_name, a, b in [
        ("val", train_end, val_end),
        ("test", val_end, n),
    ]:
        slen = b - a
        theory = {"n": slen, **{f"top{k}": k / 49 for k in (1, 3, 5, 10)}}
        results.append(row_entry(CORE_MODELS[0], split_name, theory, 0))

    # --- 马尔可夫 ---
    for split_name, (a, b) in [("val", (train_end, val_end)), ("test", (val_end, n))]:
        slen = b - a
        prev = prev_specials_for_split(specials, args.window, a, slen)
        prior_y = specials[:args.window + a] - 1
        p = markov_online_proba(prior_y, prev)
        results.append(row_entry(CORE_MODELS[1], split_name, metrics_dict(p, y[a:b]), 0))

    # 验证模型只看 train；测试模型看 train+val，各自只预测未来。
    for split_name, (a, b) in [("val", (train_end, val_end)), ("test", (val_end, n))]:
        t0 = time.perf_counter()
        hgb = fit_hgb(x_tab[:a], y[:a])
        train_sec = time.perf_counter() - t0
        proba = predict_proba_49(hgb, x_tab[a:b])
        results.append(row_entry(CORE_MODELS[2], split_name, metrics_dict(proba, y[a:b]), train_sec))

    test_rows = [r for r in results if r["split"] == "test"]
    test_rows.sort(key=lambda r: r["top1"], reverse=True)
    best = test_rows[0] if test_rows else None

    summary = {
        "title": "三模型特码预测对比",
        "dataset": str(args.csv),
        "window": args.window,
        "random_top1_theory": RANDOM_TOP1,
        "split": {"train": train_end, "val": val_end - train_end, "test": test_len},
        "evaluation_note": "验证模型仅用 train 拟合；测试模型用 train+val 拟合。理论随机为 k/49 的期望值。",
        "issues_test_range": [
            int(df.issue.iloc[args.window + val_end]),
            int(df.issue.iloc[-1]),
        ],
        "models_meta": CORE_MODELS,
        "test_ranking": test_rows,
        "all_results": results,
        "conclusion_zh": _conclusion(test_rows),
        "recommendation_zh": (
            "研究用途推荐关注测试集 Top-5/Top-10；"
            "若 Top-1 无法稳定高于 2% 约 1 个百分点，则不具备投注优势。"
        ),
        "best_on_test_top1": best["model"] if best else None,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    with args.out_json.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    fields = ["id", "model", "kind", "split", "top1", "top3", "top5", "top10", "n", "seconds", "desc"]
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k, "") for k in fields})

    print(json.dumps(summary["conclusion_zh"], ensure_ascii=False, indent=2))
    print(f"JSON: {args.out_json}")
    print(f"CSV:  {args.out_csv}")


def _conclusion(test_rows: list[dict]) -> str:
    tops = {r["id"]: r["top1"] for r in test_rows}
    hgb = tops.get("hgb", 0)
    mk = tops.get("markov", 0)
    if hgb <= RANDOM_TOP1 + 0.008 and mk <= RANDOM_TOP1 + 0.008:
        return "三支模型在测试集 Top-1 均接近理论随机（约 2%），历史号码未展现可稳定利用的规律。"
    if hgb > mk and hgb > RANDOM_TOP1 + 0.01:
        return "梯度提升略优于马尔可夫与随机，但优势很小，需更长滚动回测再判断是否偶然波动。"
    return "马尔可夫等简单规则与机器学习表现接近，优先采用更简单、可解释的马尔可夫或频率基线做对照即可。"


if __name__ == "__main__":
    main()
