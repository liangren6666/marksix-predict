"""正码回测与下一期预测共用的特征和模型配置。"""

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from ml.data import BALLS_PER_DRAW, NUM_CLASSES

REGULAR_COUNT = BALLS_PER_DRAW - 1
LOOKBACK = 30
FREQUENCY_WINDOWS = (10, LOOKBACK, 100)
WARMUP = max(FREQUENCY_WINDOWS)
HGB_CHECKPOINTS = (20, 60, 120)
DEFAULT_HGB_ITERATIONS = 60
SEED = 42


def regular_features(regular: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """每行只读目标期之前的正码。最后一行对应最新开奖之后的下一期。"""
    if len(regular) < WARMUP:
        raise ValueError(f"计算正码特征至少需要 {WARMUP} 期数据")
    indicators = np.zeros((len(regular), NUM_CLASSES), dtype=np.float32)
    indicators[np.arange(len(regular))[:, None], regular - 1] = 1
    totals = np.vstack([np.zeros(NUM_CLASSES), indicators.cumsum(axis=0)])
    last_seen = np.full(NUM_CLASSES, -WARMUP)
    features = []
    for t in range(1, len(regular) + 1):
        last_seen[indicators[t - 1].astype(bool)] = t - 1
        if t < WARMUP:
            continue
        frequencies = [(totals[t] - totals[t - w]) / w for w in FREQUENCY_WINDOWS]
        gaps = np.minimum(t - 1 - last_seen, WARMUP) / WARMUP
        features.append(np.column_stack([totals[t] / t, *frequencies, gaps]))
    return np.stack(features), indicators, totals


def make_hgb(iterations: int) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_iter=iterations,
        max_leaf_nodes=7,
        min_samples_leaf=100,
        learning_rate=0.05,
        l2_regularization=5,
        early_stopping=False,
        random_state=SEED,
    )
