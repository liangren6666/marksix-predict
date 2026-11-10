from __future__ import annotations

import torch
import torch.nn as nn


class SpecialLSTM(nn.Module):
    def __init__(self, num_classes: int = 49, hidden: int = 64, embed: int = 32):
        super().__init__()
        self.embed = nn.Embedding(num_classes, embed)
        self.lstm = nn.LSTM(embed, hidden, batch_first=True, num_layers=2, dropout=0.1)
        self.head = nn.Linear(hidden, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e = self.embed(x)
        out, _ = self.lstm(e)
        return self.head(out[:, -1, :])


class SpecialMLP(nn.Module):
    def __init__(self, in_dim: int, num_classes: int = 49, hidden: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(hidden, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
