from __future__ import annotations

import numpy as np

NUM_CLASSES = 49


def gap_vector(specials: np.ndarray, end: int, cap: int = 200) -> np.ndarray:
    """每个号码距上次出现的期数（未出现记 cap）。"""
    if cap <= 0 or not 0 <= end <= len(specials):
        raise ValueError("cap 必须为正数，end 必须在历史范围内")
    gaps = np.full(NUM_CLASSES, cap, dtype=np.float32)
    recent = specials[max(0, end - cap):end][::-1]
    numbers, first = np.unique(recent, return_index=True)
    valid = (numbers >= 1) & (numbers <= NUM_CLASSES)
    gaps[numbers[valid].astype(int) - 1] = first[valid]
    return gaps / cap


def freq_window(specials: np.ndarray, start: int, end: int) -> np.ndarray:
    """窗口内各特码出现频次（归一化）。"""
    w = specials[start:end]
    cnt = np.bincount(w - 1, minlength=NUM_CLASSES).astype(np.float32)
    total = max(len(w), 1)
    return cnt / total


def _validate_history(specials: np.ndarray, draws: np.ndarray, window: int) -> None:
    if not isinstance(window, (int, np.integer)) or window < 1:
        raise ValueError("window 必须为正整数")
    if specials.ndim != 1 or draws.shape != (len(specials), 7):
        raise ValueError("specials 必须是一维数组，draws 必须为 (T, 7)")
    if len(specials) < window:
        raise ValueError(f"至少需要 {window} 期历史，实际为 {len(specials)} 期")


def _feature_at(specials: np.ndarray, draws: np.ndarray, window: int, end: int) -> np.ndarray:
    """只读取 [0, end) 的历史；end 可以等于历史长度。"""
    w_s = specials[end - window:end]
    w_d = draws[end - window:end]
    last_k = w_s[-5:].astype(np.float32) / NUM_CLASSES
    pad = np.zeros(5, dtype=np.float32)
    pad[-len(last_k):] = last_k
    sums = w_d.sum(axis=1) / (7 * NUM_CLASSES)
    odd_ratio = (w_d % 2 == 1).sum(axis=1) / 7.0
    return np.concatenate([
        gap_vector(specials, end),
        freq_window(specials, end - window, end),
        pad,
        np.array([
            w_s[-1] / NUM_CLASSES,
            np.mean(w_s) / NUM_CLASSES,
            np.std(w_s) / NUM_CLASSES,
            np.mean(sums),
            np.std(sums),
            np.mean(odd_ratio),
            w_d[-1].sum() / (7 * NUM_CLASSES),
        ], dtype=np.float32),
    ])


def build_feature_matrix(specials: np.ndarray, draws: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    """用 [t-window, t) 及更早历史构造特征，标签为 specials[t]。"""
    _validate_history(specials, draws, window)
    if len(specials) == window:
        raise ValueError("训练数据需要比 window 多至少一期，以提供目标标签")
    xs = [_feature_at(specials, draws, window, t) for t in range(window, len(specials))]
    return np.stack(xs), (specials[window:] - 1).astype(np.int64)


def build_next_features(specials: np.ndarray, draws: np.ndarray, window: int) -> np.ndarray:
    """包含最新已开奖一期，构造真正用于下一期的单行特征。"""
    _validate_history(specials, draws, window)
    return _feature_at(specials, draws, window, len(specials)).reshape(1, -1)


def feature_names(window: int = 30) -> list[str]:
    base = [f"gap_{i+1}" for i in range(NUM_CLASSES)]
    base += [f"freq_{i+1}" for i in range(NUM_CLASSES)]
    base += [f"last_special_{i}" for i in range(5)]
    base += ["prev1_norm", "mean_w", "std_w", "sum_mean", "sum_std", "odd_mean", "last_draw_sum"]
    return base
