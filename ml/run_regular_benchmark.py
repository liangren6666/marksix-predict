"""按时间顺序回测正码预测。每期选 6 个号码，顺序不限。"""

from __future__ import annotations

import argparse
import json
from math import comb
from pathlib import Path

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from ml.data import DEFAULT_CSV, NUM_CLASSES, draws_to_matrix, load_newam6hc, temporal_split_index
from ml.regular import HGB_CHECKPOINTS, LOOKBACK, REGULAR_COUNT, SEED, WARMUP, make_hgb, regular_features

GRU_CHECKPOINTS = (5, 10, 20)


def build_inputs(regular: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    features, indicators, totals = regular_features(regular)
    sequences = np.stack([indicators[t - LOOKBACK:t] for t in range(WARMUP, len(regular))])
    return features[:-1], sequences, indicators[WARMUP:], totals


def hit_counts(scores: np.ndarray, targets: np.ndarray) -> np.ndarray:
    picks = np.argsort(-scores, axis=1, kind="stable")[:, :REGULAR_COUNT]
    return np.take_along_axis(targets, picks, axis=1).sum(axis=1).astype(int)


class RegularGRU(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.gru = nn.GRU(NUM_CLASSES, 32, batch_first=True)
        self.output = nn.Linear(32, NUM_CLASSES)

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        _, hidden = self.gru(sequence)
        return self.output(hidden[-1])


@torch.inference_mode()
def gru_scores(model: RegularGRU, x: np.ndarray) -> np.ndarray:
    model.eval()
    return model(torch.from_numpy(x)).numpy()


def fit_gru(x: np.ndarray, y: np.ndarray, epochs: int, *, validation=None):
    torch.manual_seed(SEED)
    model = RegularGRU()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=0.01)
    loss = nn.BCEWithLogitsLoss()
    loader = DataLoader(TensorDataset(torch.from_numpy(x), torch.from_numpy(y)), batch_size=64, shuffle=True)
    validation_hits = {}
    for epoch in range(1, epochs + 1):
        model.train()
        for batch, targets in loader:
            optimizer.zero_grad()
            loss(model(batch), targets).backward()
            optimizer.step()
        if validation is not None and epoch in GRU_CHECKPOINTS:
            x_val, y_val = validation
            validation_hits[epoch] = int(hit_counts(gru_scores(model, x_val), y_val).sum())
    return model, validation_hits


def uniform_hit_distribution(n: int) -> np.ndarray:
    combinations = comb(NUM_CLASSES, REGULAR_COUNT)
    per_draw = [
        comb(REGULAR_COUNT, k) * comb(NUM_CLASSES - REGULAR_COUNT, REGULAR_COUNT - k) / combinations
        for k in range(REGULAR_COUNT + 1)
    ]
    distribution = np.array([1.0])
    for _ in range(n):
        distribution = np.convolve(distribution, per_draw)
    return distribution


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_CSV.with_name("regular_benchmark.json"))
    args = parser.parse_args()

    draws = load_newam6hc(args.csv)
    # 沿用上一轮实验的测试期，便于对照。前 100 期只用于准备特征。
    train_end, val_end = temporal_split_index(len(draws) - LOOKBACK)
    train_end += LOOKBACK
    val_end += LOOKBACK
    if train_end <= WARMUP:
        parser.error(f"训练段至少需要 {WARMUP + 1} 期数据")
    features, sequences, targets, totals = build_inputs(draws_to_matrix(draws)[:, :REGULAR_COUNT])
    train = train_end - WARMUP
    val = val_end - WARMUP
    feature_count = features.shape[-1]
    x_fit = features[:val].reshape(-1, feature_count)
    x_test = features[val:].reshape(-1, feature_count)
    y_test = targets[val:]

    logreg = make_pipeline(StandardScaler(), LogisticRegression())
    logreg.fit(x_fit, targets[:val].ravel())

    hgb = make_hgb(max(HGB_CHECKPOINTS)).fit(features[:train].reshape(-1, feature_count), targets[:train].ravel())
    hgb_validation = {}
    stages = hgb.staged_predict_proba(features[train:val].reshape(-1, feature_count))
    for iteration, proba in enumerate(stages, start=1):
        if iteration in HGB_CHECKPOINTS:
            scores = proba[:, 1].reshape(-1, NUM_CLASSES)
            hgb_validation[iteration] = int(hit_counts(scores, targets[train:val]).sum())
    hgb_iterations = max(hgb_validation, key=hgb_validation.__getitem__)
    hgb = make_hgb(hgb_iterations).fit(x_fit, targets[:val].ravel())

    torch.set_num_threads(min(4, torch.get_num_threads()))
    _, gru_validation = fit_gru(
        sequences[:train], targets[:train], max(GRU_CHECKPOINTS),
        validation=(sequences[train:val], targets[train:val]),
    )
    gru_epochs = max(gru_validation, key=gru_validation.__getitem__)
    gru, _ = fit_gru(sequences[:val], targets[:val], gru_epochs)

    test_indices = np.arange(val_end, len(draws))
    scores_by_method = {
        "历史热号": totals[test_indices],
        "近30期热号": totals[test_indices] - totals[test_indices - LOOKBACK],
        "逻辑回归": logreg.predict_proba(x_test)[:, 1].reshape(-1, NUM_CLASSES),
        "梯度提升树": hgb.predict_proba(x_test)[:, 1].reshape(-1, NUM_CLASSES),
        "GRU": gru_scores(gru, sequences[val:]),
    }
    null = uniform_hit_distribution(len(y_test))
    results = {}
    for method, scores in scores_by_method.items():
        hits = hit_counts(scores, y_test)
        total = int(hits.sum())
        results[method] = {
            "total_hits": total,
            "average_hits": float(hits.mean()),
            "draws_by_hit_count_0_to_6": np.bincount(hits, minlength=REGULAR_COUNT + 1).tolist(),
            "uniform_null_tail_probability": float(null[total:].sum()),
        }

    report = {
        "dataset": args.csv.name,
        "target": "regular_numbers_top_6_unordered",
        "split": {"train": train, "validation": val - train, "test": len(y_test)},
        "test_issue_range": [int(draws.issue.iloc[val_end]), int(draws.issue.iloc[-1])],
        "uniform_expected_hits_per_draw": REGULAR_COUNT**2 / NUM_CLASSES,
        "validation_hits": {"hgb_by_iteration": hgb_validation, "gru_by_epoch": gru_validation},
        "selected_parameters": {"hgb_iterations": hgb_iterations, "gru_epochs": gru_epochs, "seed": SEED},
        "results": results,
        "note": "训练、验证、测试按期号排序。选定训练轮数后在测试段之前的数据上重训。"
                "同一测试段已用于上一轮实验，本报告用于对照；模型优势需要用新开奖确认。"
                "随机尾概率按单个方法计算，未对多个方法校正。",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
