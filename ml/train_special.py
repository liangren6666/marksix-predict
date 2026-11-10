from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from ml.models import SpecialLSTM, SpecialMLP


@dataclass
class TrainResult:
    top1_acc: float
    top3_acc: float
    top5_acc: float
    top10_acc: float
    loss: float


def _topk_acc(logits: torch.Tensor, y: torch.Tensor, k: int) -> float:
    if y.numel() == 0:
        return 0.0
    topk = torch.topk(logits, k, dim=1).indices
    return float((topk == y.unsqueeze(1)).any(dim=1).float().mean().item())


def train_lstm(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    epochs: int = 40,
    batch_size: int = 64,
    lr: float = 1e-3,
    device: str | None = None,
) -> TrainResult:
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model = SpecialLSTM().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss()

    tr_ds = TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train))
    tr_ld = DataLoader(tr_ds, batch_size=batch_size, shuffle=True)

    x_val_t = torch.from_numpy(x_val).to(device)
    y_val_t = torch.from_numpy(y_val).to(device)

    for _ in range(epochs):
        model.train()
        for xb, yb in tr_ld:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = crit(model(xb), yb)
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        logits = model(x_val_t)
        loss = float(crit(logits, y_val_t).item())
        top1 = _topk_acc(logits, y_val_t, 1)
        top3 = _topk_acc(logits, y_val_t, 3)
        top5 = _topk_acc(logits, y_val_t, 5)
        top10 = _topk_acc(logits, y_val_t, 10)
    return TrainResult(top1, top3, top5, top10, loss)


def train_mlp(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    epochs: int = 60,
    batch_size: int = 64,
    lr: float = 1e-3,
    device: str | None = None,
) -> TrainResult:
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model = SpecialMLP(in_dim=x_train.shape[1]).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss()

    tr_ds = TensorDataset(
        torch.from_numpy(x_train.astype(np.float32)),
        torch.from_numpy(y_train),
    )
    tr_ld = DataLoader(tr_ds, batch_size=batch_size, shuffle=True)
    x_val_t = torch.from_numpy(x_val.astype(np.float32)).to(device)
    y_val_t = torch.from_numpy(y_val).to(device)

    for _ in range(epochs):
        model.train()
        for xb, yb in tr_ld:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = crit(model(xb), yb)
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        logits = model(x_val_t)
        loss = float(crit(logits, y_val_t).item())
        top1 = _topk_acc(logits, y_val_t, 1)
        top3 = _topk_acc(logits, y_val_t, 3)
        top5 = _topk_acc(logits, y_val_t, 5)
        top10 = _topk_acc(logits, y_val_t, 10)
    return TrainResult(top1, top3, top5, top10, loss)
