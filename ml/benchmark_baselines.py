from __future__ import annotations

import numpy as np
from collections import Counter, defaultdict


def uniform_proba(n: int, seed: int = 42) -> np.ndarray:
    """每期独立均匀分布（用 Gumbel-max 打破 argmax 并列）。"""
    rng = np.random.default_rng(seed)
    logits = rng.random((n, 49))
    logits /= logits.sum(axis=1, keepdims=True)
    return logits.astype(np.float64)


def frequency_proba(train_y: np.ndarray, n_test: int) -> np.ndarray:
    cnt = np.bincount(train_y, minlength=49).astype(np.float64)
    if cnt.sum() == 0:
        return uniform_proba(n_test)
    p = cnt / cnt.sum()
    return np.tile(p, (n_test, 1))


def markov_online_proba(history: np.ndarray, test_prev: np.ndarray) -> np.ndarray:
    """history: 0..48 已知历史；test_prev[i]=上一期特码(0..48)。"""
    trans: dict[int, np.ndarray] = {}
    counts: dict[int, np.ndarray] = defaultdict(lambda: np.zeros(49))
    global_cnt = np.bincount(history, minlength=49).astype(np.float64)
    if global_cnt.sum() == 0:
        global_cnt = np.ones(49)
    global_p = global_cnt / global_cnt.sum()

    for a, b in zip(history[:-1], history[1:]):
        counts[a][b] += 1

    for a, c in counts.items():
        s = c.sum()
        trans[a] = (c + 1.0) / (s + 49.0) if s > 0 else global_p

    rows = []
    for prev in test_prev:
        rows.append(trans.get(int(prev), global_p))
    return np.stack(rows)


def repeat_last_proba(test_prev: np.ndarray) -> np.ndarray:
    rows = np.full((len(test_prev), 49), 1e-6)
    for i, prev in enumerate(test_prev):
        rows[i, int(prev)] = 1.0 - 48 * 1e-6
        rows[i] /= rows[i].sum()
    return rows


def prev_specials_for_split(specials: np.ndarray, window: int, start_idx: int, length: int) -> np.ndarray:
    """start_idx: y 数组上的起点索引，对应 specials[window+start_idx-1] 为第一期上一期。"""
    out = []
    for j in range(length):
        t = window + start_idx + j
        out.append(specials[t - 1] - 1)
    return np.array(out, dtype=np.int64)
