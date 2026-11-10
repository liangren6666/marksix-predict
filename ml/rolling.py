from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ml.evaluate import metrics_dict


@dataclass
class RollingResult:
    metrics: dict
    fold_metrics: list[dict]


def rolling_evaluate(
    proba_fn,
    x: np.ndarray,
    y: np.ndarray,
    *,
    min_train: int,
    step: int = 1,
) -> RollingResult:
    """
    扩展窗口回测：在 [min_train, len) 上每期用过去全部样本训练并预测当期。
    proba_fn(train_x, train_y, test_x) -> proba (1, 49)
    用于严格模拟“当时只能看到过去”的场景（较慢，用子采样）。
    """
    folds = []
    preds = []
    truths = []

    indices = range(min_train, len(y), step)
    for t in indices:
        px = x[:t]
        py = y[:t]
        p = proba_fn(px, py, x[t : t + 1])
        if p.ndim == 1:
            p = p.reshape(1, -1)
        preds.append(p[0])
        truths.append(y[t])

    if not truths:
        return RollingResult(metrics={"n": 0}, fold_metrics=[])

    proba = np.stack(preds)
    yy = np.array(truths)
    return RollingResult(metrics=metrics_dict(proba, yy), fold_metrics=folds)
