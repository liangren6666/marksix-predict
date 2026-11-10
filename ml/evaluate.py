from __future__ import annotations

import numpy as np


def topk_accuracy(proba: np.ndarray, y: np.ndarray, k: int) -> float:
    if len(y) == 0:
        return 0.0
    topk = np.argpartition(proba, -k, axis=1)[:, -k:]
    return float(np.mean([y[i] in topk[i] for i in range(len(y))]))


def top1_accuracy(proba: np.ndarray, y: np.ndarray) -> float:
    if len(y) == 0:
        return 0.0
    pred = np.argmax(proba, axis=1)
    return float(np.mean(pred == y))


def metrics_dict(proba: np.ndarray, y: np.ndarray) -> dict:
    return {
        "n": int(len(y)),
        "top1": top1_accuracy(proba, y),
        "top3": topk_accuracy(proba, y, 3),
        "top5": topk_accuracy(proba, y, 5),
        "top10": topk_accuracy(proba, y, 10),
    }
