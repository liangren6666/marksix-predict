"""
新澳门彩特码预测主流水线：
- 时间顺序划分 train/val/test（测试集封存）
- 特征：遗漏 + 窗口频次 + 近期统计
- 模型：HistGradientBoosting（主） + 多项逻辑回归（辅）
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.baselines import frequency_top1, markov_order1
from ml.data import DEFAULT_CSV, load_newam6hc, temporal_split_index
from ml.evaluate import metrics_dict
from ml.features import build_feature_matrix
from ml.probability import predict_proba_49

RANDOM_TOP1 = 1 / 49


def _repeat_last(specials: np.ndarray, test_start: int, test_len: int) -> dict:
    hits = sum(
        1 for j in range(test_len) if specials[test_start + j] == specials[test_start + j - 1]
    )
    return {"name": "repeat_last", "top1_acc": hits / max(test_len, 1)}


def train_hgb(x_train, y_train):
    clf = HistGradientBoostingClassifier(
        max_depth=6,
        max_iter=280,
        learning_rate=0.06,
        l2_regularization=1.0,
        min_samples_leaf=40,
        early_stopping=True,
        validation_fraction=0.12 if len(x_train) > 200 else 0.1,
        n_iter_no_change=15,
        random_state=42,
    )
    clf.fit(x_train, y_train)
    return clf


def train_logreg(x_train, y_train):
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=800,
                    C=0.35,
                    random_state=42,
                ),
            ),
        ]
    )
    pipe.fit(x_train, y_train)
    return pipe


def blend_proba(p1: np.ndarray, p2: np.ndarray, w: float = 0.75) -> np.ndarray:
    return w * p1 + (1.0 - w) * p2


def main() -> None:
    parser = argparse.ArgumentParser(description="训练并封存测试集评估")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--window", type=int, default=30)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument(
        "--out-dir", type=Path, default=Path(__file__).resolve().parents[1] / "models"
    )
    parser.add_argument(
        "--report", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "train_report.json"
    )
    args = parser.parse_args()

    df = load_newam6hc(args.csv)
    specials = df["special"].to_numpy()
    draws = df[[f"n{i}" for i in range(1, 7)] + ["special"]].to_numpy()

    x, y = build_feature_matrix(specials, draws, args.window)
    n = len(y)
    train_end, val_end = temporal_split_index(n, args.train_ratio, args.val_ratio)

    x_train, y_train = x[:train_end], y[:train_end]
    x_val, y_val = x[train_end:val_end], y[train_end:val_end]
    x_test, y_test = x[val_end:], y[val_end:]

    # --- 训练（不用测试集） ---
    hgb = train_hgb(x_train, y_train)
    logreg = train_logreg(x_train, y_train)
    p_val_h = predict_proba_49(hgb, x_val)
    p_val_l = predict_proba_49(logreg, x_val)

    # 两个模型都未见过验证标签；缓存概率，避免每个权重重复推理。
    best_w, best_top1 = 0.7, -1.0
    for w in np.linspace(0.5, 0.95, 10):
        m = metrics_dict(blend_proba(p_val_h, p_val_l, w), y_val)
        if m["top1"] > best_top1:
            best_top1 = m["top1"]
            best_w = float(w)
    p_val = blend_proba(p_val_h, p_val_l, best_w)

    # 权重确定后用 train+val 重训；test 从未参与拟合或调参。
    hgb = train_hgb(x[:val_end], y[:val_end])
    logreg = train_logreg(x[:val_end], y[:val_end])
    p_test_h = predict_proba_49(hgb, x_test)
    p_test_l = predict_proba_49(logreg, x_test)
    p_test = blend_proba(p_test_h, p_test_l, best_w)

    # 统计基线（仅测试段对应特码）
    test_special_start = args.window + val_end
    test_specials = specials[test_special_start:]
    train_specials = specials[:test_special_start]

    baselines = {
        "random_top1": RANDOM_TOP1,
        "frequency_top1": frequency_top1(train_specials, test_specials),
        "markov_order1": markov_order1(train_specials, test_specials),
        "repeat_last": _repeat_last(specials, test_special_start, len(test_specials)),
    }

    report = {
        "dataset": str(args.csv),
        "target": "next_special",
        "window": args.window,
        "n_samples": n,
        "split": {
            "train": train_end,
            "val": val_end - train_end,
            "test": n - val_end,
            "note": "test 集在训练与调参全程未参与",
            "validation_note": "验证集仅用于选择融合权重；验证成绩属于调参成绩，最终以测试集为准",
            "test_fit_note": "权重固定后，两个模型均使用 train+val 重训并保存",
        },
        "models": {
            "primary": "HistGradientBoostingClassifier",
            "secondary": "LogisticRegression(multinomial)",
            "blend_weight_hgb": best_w,
        },
        "metrics": {
            "val_ensemble": metrics_dict(p_val, y_val),
            "test_hgb": metrics_dict(p_test_h, y_test),
            "test_logreg": metrics_dict(p_test_l, y_test),
            "test_ensemble": metrics_dict(p_test, y_test),
        },
        "baselines_test": baselines,
        "verdict": _verdict(metrics_dict(p_test, y_test), baselines),
        "issues_test_range": [
            int(df.issue.iloc[test_special_start]),
            int(df.issue.iloc[test_special_start + len(test_specials) - 1]),
        ],
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "hgb_special.pkl").open("wb") as f:
        pickle.dump(hgb, f)
    with (args.out_dir / "logreg_special.pkl").open("wb") as f:
        pickle.dump({"model": logreg, "blend_w": best_w, "window": args.window}, f)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n模型: {args.out_dir}")
    print(f"报告: {args.report}")


def _verdict(m: dict, baselines: dict) -> str:
    test_top1 = m["top1"]
    markov = baselines["markov_order1"]["top1_acc"]
    if test_top1 <= RANDOM_TOP1 + 0.003:
        return "无优势：测试 Top-1 接近随机，不建议用于预测下注。"
    if test_top1 < markov:
        return "弱于马尔可夫基线：集成模型未学到可泛化结构。"
    if test_top1 < RANDOM_TOP1 + 0.015:
        return "边际优势：略优于随机/简单规则，但不足以覆盖实际成本。"
    return "需更长滚动回测验证：初步优于基线，但仍可能为样本波动。"


if __name__ == "__main__":
    main()
