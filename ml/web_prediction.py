"""为本地网页按公历日期生成正码和特码候选。"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ml.calendar_issue import date_to_issue, issue_to_date
from ml.data import DEFAULT_CSV, NUM_CLASSES, draws_to_matrix, load_newam6hc
from ml.features import build_feature_matrix, build_next_features
from ml.next_reference import DEFAULT_MODEL_DIR, hgb_ensemble_topk
from ml.probability import predict_proba_49
from ml.regular import (
    DEFAULT_HGB_ITERATIONS,
    HGB_CHECKPOINTS,
    REGULAR_COUNT,
    WARMUP,
    make_hgb,
    regular_features,
)
from ml.run_train import train_hgb, train_logreg

REGULAR_CANDIDATE_COUNT = 20
SPECIAL_CANDIDATE_COUNT = 20
FORECAST_HORIZON_DAYS = 366
SPECIAL_WINDOW = 30
SPECIAL_BLEND = 0.75
CACHE_VERSION = 1


def parse_day(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("日期格式应为 YYYY-MM-DD") from exc


def selected_iterations(csv: Path) -> int:
    report_path = csv.with_name("regular_benchmark.json")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        iterations = report["selected_parameters"]["hgb_iterations"]
        if report["dataset"] == csv.name and isinstance(iterations, int) and iterations in HGB_CHECKPOINTS:
            return iterations
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return DEFAULT_HGB_ITERATIONS


def _write_json(path: Path, payload) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass


def regular_ranking(df: pd.DataFrame, csv: Path, model_dir: Path) -> list[dict]:
    if len(df) <= WARMUP:
        raise ValueError(f"拟合正码模型至少需要 {WARMUP + 1} 期数据")
    iterations = selected_iterations(csv)
    cache = model_dir / "date_cache" / (
        f"regular-{int(df.issue.iloc[-1])}-{len(df)}-{iterations}-v{CACHE_VERSION}.json"
    )
    scores = None
    if cache.is_file():
        try:
            payload = json.loads(cache.read_text(encoding="utf-8"))
            if isinstance(payload, list) and len(payload) == NUM_CLASSES:
                scores = np.asarray(payload, dtype=float)
        except (OSError, ValueError, TypeError):
            scores = None
    if scores is None:
        regular = draws_to_matrix(df)[:, :REGULAR_COUNT]
        features, indicators, _ = regular_features(regular)
        model = make_hgb(iterations)
        model.fit(features[:-1].reshape(-1, features.shape[-1]), indicators[WARMUP:].ravel())
        scores = np.asarray(model.predict_proba(features[-1])[:, 1], dtype=float)
        _write_json(cache, [float(value) for value in scores])
    return [
        {"num": int(index) + 1, "rank": rank, "score": round(float(scores[index]), 6)}
        for rank, index in enumerate(np.argsort(-scores, kind="stable"), start=1)
    ]


def special_ranking_from_history(df: pd.DataFrame, model_dir: Path) -> list[dict]:
    """只用目标日之前的开奖，重新拟合特码模型。"""
    if len(df) <= SPECIAL_WINDOW:
        raise ValueError(f"拟合特码模型至少需要 {SPECIAL_WINDOW + 1} 期数据")
    cache = model_dir / "date_cache" / f"special-{int(df.issue.iloc[-1])}-{len(df)}-v{CACHE_VERSION}.pkl"
    pack = None
    if cache.is_file():
        try:
            with cache.open("rb") as handle:
                pack = pickle.load(handle)
        except (OSError, pickle.UnpicklingError, EOFError):
            pack = None
    specials = df["special"].to_numpy()
    draws = draws_to_matrix(df)
    if not isinstance(pack, dict) or "hgb" not in pack or "logreg" not in pack:
        features, labels = build_feature_matrix(specials, draws, SPECIAL_WINDOW)
        pack = {"hgb": train_hgb(features, labels), "logreg": train_logreg(features, labels)}
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            with cache.open("wb") as handle:
                pickle.dump(pack, handle)
        except OSError:
            pass
    last_row = build_next_features(specials, draws, SPECIAL_WINDOW)
    proba = SPECIAL_BLEND * predict_proba_49(pack["hgb"], last_row)
    proba += (1 - SPECIAL_BLEND) * predict_proba_49(pack["logreg"], last_row)
    return [
        {"num": int(number), "rank": rank, "score": round(float(proba[0, number - 1]), 5)}
        for rank, number in enumerate(np.argsort(-proba[0], kind="stable") + 1, start=1)
    ]


def _actual_draw(df: pd.DataFrame, issue: int) -> dict | None:
    matched = df[df.issue == issue]
    if matched.empty:
        return None
    row = matched.iloc[0]
    return {
        "issue": int(row.issue),
        "regular": [int(row[f"n{i}"]) for i in range(1, 7)],
        "special": int(row.special),
    }


def _bounds(df: pd.DataFrame) -> tuple[date, date]:
    earliest_index = min(WARMUP + 1, len(df) - 1)
    start = issue_to_date(int(df.issue.iloc[earliest_index]))
    end = issue_to_date(int(df.issue.iloc[-1])) + timedelta(days=FORECAST_HORIZON_DAYS)
    return start, end


def _fit_regular_model(df: pd.DataFrame, csv: Path):
    regular = draws_to_matrix(df)[:, :REGULAR_COUNT]
    features, indicators, _ = regular_features(regular)
    model = make_hgb(selected_iterations(csv))
    model.fit(features[:-1].reshape(-1, features.shape[-1]), indicators[WARMUP:].ravel())
    return model


def _load_special_pack(model_dir: Path) -> dict:
    hgb_path = model_dir / "hgb_special.pkl"
    logreg_path = model_dir / "logreg_special.pkl"
    if not hgb_path.is_file() or not logreg_path.is_file():
        raise FileNotFoundError("缺少特码模型，请先准备 models 目录里的模型文件")
    with hgb_path.open("rb") as handle:
        hgb = pickle.load(handle)
    with logreg_path.open("rb") as handle:
        packed = pickle.load(handle)
    return {
        "hgb": hgb,
        "logreg": packed["model"],
        "blend": float(packed["blend_w"]),
        "window": int(packed["window"]),
    }


_PREPARED: dict[tuple, tuple] = {}


def _prepare_models(df: pd.DataFrame, csv: Path, model_dir: Path):
    key = (str(csv.resolve()) if csv.exists() else str(csv), int(df.issue.iloc[-1]), len(df))
    if key not in _PREPARED:
        _PREPARED[key] = (_fit_regular_model(df, csv), _load_special_pack(model_dir))
    return _PREPARED[key]


def _ranking_from_scores(scores: np.ndarray) -> list[dict]:
    return [
        {"num": int(index) + 1, "rank": rank, "score": round(float(scores[index]), 6)}
        for rank, index in enumerate(np.argsort(-scores, kind="stable"), start=1)
    ]


def _rank_draws(draws: np.ndarray, regular_model, special_pack: dict) -> tuple[list[dict], list[dict]]:
    features, _, _ = regular_features(draws[:, :REGULAR_COUNT])
    regular_scores = np.asarray(regular_model.predict_proba(features[-1])[:, 1], dtype=float)
    last_row = build_next_features(draws[:, -1], draws, special_pack["window"])
    proba = special_pack["blend"] * predict_proba_49(special_pack["hgb"], last_row)
    proba += (1 - special_pack["blend"]) * predict_proba_49(special_pack["logreg"], last_row)
    return _ranking_from_scores(regular_scores), _ranking_from_scores(proba[0])


def _synthetic_draw(regular_ranking: list[dict], special_ranking: list[dict]) -> np.ndarray:
    regular: list[int] = []
    for item in regular_ranking:
        number = int(item["num"])
        if number not in regular:
            regular.append(number)
        if len(regular) == REGULAR_COUNT:
            break
    used = set(regular)
    special = next(int(item["num"]) for item in special_ranking if int(item["num"]) not in used)
    return np.asarray([*regular, special], dtype=np.int32)


def _project(draws: np.ndarray, steps: int, regular_model, special_pack) -> tuple[list[dict], list[dict]]:
    """把模型自己的预测逐日接上，直到目标日。steps 为 1 时就是下一期。"""
    if steps < 1:
        raise ValueError("预测步数至少为 1")
    current = np.array(draws, copy=True)
    for _ in range(steps - 1):
        regular_ranking, special_ranking = _rank_draws(current, regular_model, special_pack)
        current = np.vstack([current, _synthetic_draw(regular_ranking, special_ranking)])
    return _rank_draws(current, regular_model, special_pack)


def _assemble(
    df: pd.DataFrame,
    ranking: list[dict],
    special_ranking: list[dict],
    *,
    target_day: date,
    full: pd.DataFrame,
    actual: dict | None,
    special_model: str,
    steps: int = 1,
) -> dict:
    regular_picks = [item["num"] for item in ranking[:REGULAR_CANDIDATE_COUNT]]
    special_picks = [item["num"] for item in special_ranking[:SPECIAL_CANDIDATE_COUNT]]
    special_pick = next(
        (item["num"] for item in special_ranking if item["num"] not in regular_picks),
        special_ranking[0]["num"],
    )
    draws = draws_to_matrix(df)
    last_issue = int(df.issue.iloc[-1])
    last_day = issue_to_date(last_issue)
    if steps > 1:
        note = (
            f"最新开奖是 {last_issue} 期（{last_day.isoformat()}）。"
            f"{target_day.isoformat()} 之前还有 {steps - 1} 天未开出，"
            "这几天按模型逐日往后推，所以和下一期的号码不同。"
        )
    elif actual:
        note = "这一天已经开奖。下面的 20 个正码和 20 个特码只使用了开奖前的记录。"
    else:
        note = (
            f"预测 {target_day.isoformat()}（第 {date_to_issue(target_day)} 期），"
            f"依据截至 {last_issue} 期的开奖。"
        )
    start, end = _bounds(full)
    return {
        "lottery": "新澳门彩",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "draw_count": len(df),
        "target": {"date": target_day.isoformat(), "issue": date_to_issue(target_day)},
        "selectable_from": start.isoformat(),
        "selectable_to": end.isoformat(),
        "note": note,
        "actual": actual,
        "last_draw": {
            "issue": last_issue,
            "date": last_day.isoformat(),
            "regular": draws[-1, :REGULAR_COUNT].tolist(),
            "special": int(draws[-1, -1]),
        },
        "regular": {"model": "梯度提升树（HGB）", "picks": regular_picks, "ranking": ranking},
        "special": {
            "model": special_model,
            "pick": special_pick,
            "picks": special_picks,
            "ranking": special_ranking,
        },
    }


def build_prediction(
    csv: Path = DEFAULT_CSV,
    model_dir: Path = DEFAULT_MODEL_DIR,
    day: date | None = None,
) -> dict:
    if day is None:
        special, df = hgb_ensemble_topk(model_dir, topk=NUM_CLASSES, csv=csv)
        ranking = regular_ranking(df, csv, model_dir)
        special_ranking = [
            {"num": item["num"], "rank": item["rank"], "score": item["p"]}
            for item in special["picks"]
        ]
        target_day = issue_to_date(int(df.issue.iloc[-1])) + timedelta(days=1)
        return _assemble(
            df,
            ranking,
            special_ranking,
            target_day=target_day,
            full=df,
            actual=None,
            special_model="梯度提升树 + 逻辑回归",
        )

    full = load_newam6hc(csv)
    start, end = _bounds(full)
    if day < start or day > end:
        raise ValueError(f"日期需在 {start.isoformat()} 到 {end.isoformat()} 之间")
    target_issue = date_to_issue(day)
    last_issue = int(full.issue.iloc[-1])
    last_day = issue_to_date(last_issue)
    steps = (day - last_day).days
    if target_issue > last_issue:
        regular_model, special_pack = _prepare_models(full, csv, model_dir)
        ranking, special_ranking = _project(
            draws_to_matrix(full), max(steps, 1), regular_model, special_pack
        )
        return _assemble(
            full,
            ranking,
            special_ranking,
            target_day=day,
            full=full,
            actual=None,
            special_model="梯度提升树 + 逻辑回归",
            steps=max(steps, 1),
        )
    else:
        df = full[full.issue < target_issue].reset_index(drop=True)
        if len(df) <= WARMUP:
            raise ValueError(f"这一天之前的开奖不足 {WARMUP + 1} 期，无法计算")
        special_ranking = special_ranking_from_history(df, model_dir)
        model_name = "梯度提升树 + 逻辑回归（开奖前重拟合）"
    ranking = regular_ranking(df, csv, model_dir)
    return _assemble(
        df,
        ranking,
        special_ranking,
        target_day=day,
        full=full,
        actual=_actual_draw(full, target_issue),
        special_model=model_name,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="要预测的公历日期，格式 YYYY-MM-DD")
    parser.add_argument("--out", type=Path, help="另存一份网页参考快照")
    args = parser.parse_args()
    try:
        result = build_prediction(day=parse_day(args.date) if args.date else None)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(2) from exc
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
