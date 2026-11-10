from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(os.environ["LOTTERY_ROOT"]) if os.environ.get("LOTTERY_ROOT") else Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "newam6hc_5y_verified.csv"
NUM_CLASSES = 49
BALLS_PER_DRAW = 7


def load_newam6hc(path: Path | None = None) -> pd.DataFrame:
    path = path or DEFAULT_CSV
    df = pd.read_csv(path, encoding="utf-8-sig")
    cols = ["issue", "year", "seq", "n1", "n2", "n3", "n4", "n5", "n6", "special"]
    missing = sorted(set(cols) - set(df.columns))
    if missing:
        raise ValueError(f"CSV 缺少字段: {', '.join(missing)}")
    if df.empty:
        raise ValueError("CSV 没有可用于训练的开奖数据")
    values = df[cols].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(values.to_numpy()).all() or (values % 1 != 0).any().any():
        raise ValueError("期号、年份、序号和球号必须为非空整数")
    df = values.astype(np.int64)
    if df.issue.duplicated().any():
        raise ValueError("CSV 存在重复期号，请先核对数据")
    if ((df.year < 1) | (df.seq < 1) | (df.seq > 999) | (df.issue != df.year * 1000 + df.seq)).any():
        raise ValueError("期号与年份/序号不一致")
    balls = df[[f"n{i}" for i in range(1, 7)] + ["special"]].to_numpy()
    if np.any((balls < 1) | (balls > NUM_CLASSES)):
        raise ValueError("球号必须在 1..49 范围内")
    if np.any(np.diff(np.sort(balls, axis=1), axis=1) == 0):
        raise ValueError("同一期的 7 个球号不能重复")
    df = df.sort_values("issue").reset_index(drop=True)
    return df


def draws_to_matrix(df: pd.DataFrame) -> np.ndarray:
    """shape (T, 7)，值为 1..49。"""
    ball_cols = [f"n{i}" for i in range(1, 7)] + ["special"]
    return df[ball_cols].to_numpy(dtype=np.int32)


def one_hot_draw(nums: np.ndarray) -> np.ndarray:
    """7x49 multi-hot（每期 7 个号各激活一位）。"""
    mat = np.zeros((len(nums), NUM_CLASSES), dtype=np.float32)
    for i, n in enumerate(nums):
        if 1 <= n <= NUM_CLASSES:
            mat[i, n - 1] = 1.0
    return mat


def build_special_windows(
    specials: np.ndarray, window: int
) -> tuple[np.ndarray, np.ndarray]:
    """用过去 window 期特码（0..48）预测下一期特码。"""
    x_list, y_list = [], []
    for t in range(window, len(specials)):
        hist = specials[t - window : t] - 1
        x_list.append(hist)
        y_list.append(specials[t] - 1)
    return np.array(x_list, dtype=np.int64), np.array(y_list, dtype=np.int64)


def build_multihot_windows(
    draws: np.ndarray, window: int
) -> tuple[np.ndarray, np.ndarray]:
    """用过去 window 期的 7 球 multi-hot 预测下一期特码。"""
    xs, ys = [], []
    for t in range(window, len(draws)):
        chunk = draws[t - window : t]
        feat = one_hot_draw(chunk.reshape(-1)).reshape(window * BALLS_PER_DRAW, NUM_CLASSES)
        xs.append(feat.sum(axis=0))
        ys.append(draws[t, -1] - 1)
    return np.stack(xs), np.array(ys, dtype=np.int64)


def temporal_split_index(n: int, train_ratio: float = 0.7, val_ratio: float = 0.15) -> tuple[int, int]:
    if not (0 < train_ratio < 1 and 0 < val_ratio < 1 and train_ratio + val_ratio < 1):
        raise ValueError("训练/验证比例必须大于 0，且总和小于 1")
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    if not 0 < train_end < val_end < n:
        raise ValueError("样本不足，无法得到非空的训练、验证和测试集")
    return train_end, val_end
