"""生成「下一期特码参考」结构，供 CLI 与网站 JSON 使用。"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ml.data import DEFAULT_CSV, ROOT, load_newam6hc
from ml.features import build_feature_matrix, build_next_features
from ml.probability import predict_proba_49

DEFAULT_MODEL_DIR = ROOT / "models"
DEFAULT_OUT = ROOT / "data" / "next_reference.json"

RANDOM_TOP1 = 1 / 49


def markov_predict(specials: np.ndarray, top_n: int = 5) -> dict:
    prev = int(specials[-1])
    transitions: Counter[int] = Counter()
    for a, b in zip(specials[:-1], specials[1:], strict=False):
        if int(a) == prev:
            transitions[int(b)] += 1
    global_top = int(Counter(specials).most_common(1)[0][0])
    if transitions:
        top1 = transitions.most_common(1)[0][0]
        support = int(transitions[top1])
        candidates = [
            {"num": int(k), "count": int(v)} for k, v in transitions.most_common(top_n)
        ]
    else:
        top1 = global_top
        support = 0
        candidates = [{"num": global_top, "count": int(np.sum(specials == global_top))}]
    return {
        "prev_special": prev,
        "top1": top1,
        "support": support,
        "candidates": candidates,
        "fallback_global_top": global_top if not transitions else None,
    }


def hgb_ensemble_topk(
    model_dir: Path,
    topk: int = 10,
    csv: Path | None = None,
):
    import pickle

    if not isinstance(topk, int) or not 1 <= topk <= 49:
        raise ValueError("topk 必须为 1..49 的整数")
    logreg_path = model_dir / "logreg_special.pkl"
    hgb_path = model_dir / "hgb_special.pkl"
    if not logreg_path.is_file() or not hgb_path.is_file():
        raise FileNotFoundError(
            f"缺少模型文件，请先运行: python -m ml.run_train (目录 {model_dir})"
        )

    with logreg_path.open("rb") as f:
        pack = pickle.load(f)
    with hgb_path.open("rb") as f:
        hgb = pickle.load(f)
    w = pack["blend_w"]
    if not 0 <= w <= 1:
        raise ValueError("模型融合权重必须在 0..1 范围内")
    window = pack["window"]
    logreg = pack["model"]

    df = load_newam6hc(csv)
    specials = df["special"].to_numpy()
    draws = df[[f"n{i}" for i in range(1, 7)] + ["special"]].to_numpy()
    last_x = build_next_features(specials, draws, window)

    proba = w * predict_proba_49(hgb, last_x) + (1 - w) * predict_proba_49(logreg, last_x)
    order = np.argsort(-proba[0], kind="stable")[:topk]
    picks = [
        {"rank": i + 1, "num": int(n), "p": round(float(proba[0, n - 1]), 5)}
        for i, n in enumerate(order + 1)
    ]
    meta = {
        "blend_weight_hgb": float(w),
        "window": int(window),
        "topk": int(topk),
        "top1": picks[0]["num"],
        "picks": picks,
    }
    return meta, df


def build_next_reference(
    *,
    model_dir: Path = DEFAULT_MODEL_DIR,
    csv: Path | None = None,
    topk: int = 10,
) -> dict:
    csv = csv or DEFAULT_CSV
    hgb_block, df = hgb_ensemble_topk(model_dir, topk=topk, csv=csv)
    specials = df["special"].to_numpy()
    last = df.iloc[-1]
    nums = [int(last[f"n{i}"]) for i in range(1, 7)]
    special = int(last["special"])
    last_issue = int(last["issue"])
    try:
        next_issue_hint = last_issue + 1
    except Exception:
        next_issue_hint = None

    markov = markov_predict(specials, top_n=5)

    return {
        "title": "新澳门彩 · 下一期特码参考",
        "lottery_key": "newam6hc",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "dataset": str(csv.resolve()) if csv.is_file() else str(csv),
        "random_top1_theory": RANDOM_TOP1,
        "last_draw": {
            "issue": last_issue,
            "nums": nums,
            "special": special,
        },
        "next_issue_hint": next_issue_hint,
        "target": "next_special",
        "target_note": "仅预测下一期「特码」（1 个号码），不包含 6 个正码组合。",
        "models": {
            "hgb_ensemble": {
                "id": "hgb",
                "label": "梯度提升 (HGB)",
                "kind": "ml",
                "desc": "遗漏、窗口频次等特征 + HGB 与逻辑回归融合。",
                **hgb_block,
            },
            "markov_order1": {
                "id": "markov",
                "label": "马尔可夫链",
                "kind": "baseline",
                "desc": "在全部历史中统计：上一期特码为本期时，下期最常出现的特码。",
                **markov,
            },
            "repeat_last": {
                "id": "repeat_last",
                "label": "沿用上一期",
                "kind": "baseline",
                "num": special,
                "desc": "简单对照：猜测下期特码与本期相同（长期命中率接近随机）。",
            },
        },
        "disclaimer_zh":
            "历史回测显示各方法 Top-1 命中率约 2%，与理论随机接近；本页仅供研究参考，不构成投注建议。",
        "refresh_steps": [
            "python fetch_marksix.py --kind newam6hc",
            "python verify_marksix.py --kind newam6hc",
            "python -m ml.run_train",
            "python -m ml.export_next_reference",
            "python scripts/sync_viz_data.py",
        ],
    }


def write_next_reference(out: Path = DEFAULT_OUT, **kwargs) -> dict:
    payload = build_next_reference(**kwargs)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload
