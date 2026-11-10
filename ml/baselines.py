from __future__ import annotations

import numpy as np
from collections import Counter


def uniform_random(n: int, seed: int = 42) -> float:
    rng = np.random.default_rng(seed)
    return 1.0 / 49


def frequency_top1(train_specials: np.ndarray, test_specials: np.ndarray) -> dict:
    """全历史最 frequent 特码，对测试集始终猜同一号。"""
    top = Counter(train_specials).most_common(1)[0][0]
    hits = np.mean(test_specials == top)
    return {"name": "frequency_top1", "top_num": int(top), "top1_acc": float(hits)}


def repeat_last(window_specials: np.ndarray, test_specials: np.ndarray, window: int) -> dict:
    """猜上一期特码（赌徒谬误基线）。"""
    if len(test_specials) == 0:
        return {"name": "repeat_last", "top1_acc": 0.0}
    preds = window_specials[-len(test_specials) - 1 : -1]
    hits = np.mean(preds == test_specials)
    return {"name": "repeat_last", "top1_acc": float(hits)}


def markov_order1(train_specials: np.ndarray, test_specials: np.ndarray) -> dict:
    """一阶转移：P(next|prev)，无平滑时回退全局众数。"""
    transitions: dict[int, Counter] = {}
    for a, b in zip(train_specials[:-1], train_specials[1:]):
        transitions.setdefault(a, Counter())[b] += 1
    global_top = Counter(train_specials).most_common(1)[0][0]
    correct = 0
    for i in range(len(test_specials)):
        prev = test_specials[i - 1] if i > 0 else train_specials[-1]
        if prev in transitions and transitions[prev]:
            pred = transitions[prev].most_common(1)[0][0]
        else:
            pred = global_top
        if pred == test_specials[i]:
            correct += 1
    return {"name": "markov_order1", "top1_acc": correct / max(len(test_specials), 1)}


def topk_hit_rate(probs: np.ndarray, y: np.ndarray, k: int) -> float:
    if len(y) == 0:
        return 0.0
    topk = np.argpartition(probs, -k, axis=1)[:, -k:]
    return float(np.mean([y[i] in topk[i] for i in range(len(y))]))
