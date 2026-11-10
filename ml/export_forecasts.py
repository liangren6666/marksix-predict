"""把一段日期内的正码、特码预测写成网页可直接读取的 JSON。"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from ml.calendar_issue import issue_to_date
from ml.data import DEFAULT_CSV, ROOT, draws_to_matrix, load_newam6hc
from ml.next_reference import DEFAULT_MODEL_DIR
from ml.web_prediction import (
    _actual_draw,
    _assemble,
    _prepare_models,
    _rank_draws,
    _synthetic_draw,
)

PAST_DAYS = 45
FUTURE_DAYS = 90
OUT = ROOT / "data" / "forecasts.json"


def build_book(
    csv: Path = DEFAULT_CSV,
    model_dir: Path = DEFAULT_MODEL_DIR,
    *,
    past_days: int = PAST_DAYS,
    future_days: int = FUTURE_DAYS,
    today: date | None = None,
) -> dict:
    full = load_newam6hc(csv)
    draws = draws_to_matrix(full)
    regular_model, special_pack = _prepare_models(full, csv, model_dir)
    last_issue = int(full.issue.iloc[-1])
    last_day = issue_to_date(last_issue)
    start_index = max(len(full) - past_days, 101)
    days = {}

    for index in range(start_index, len(full)):
        target_issue = int(full.issue.iloc[index])
        target_day = issue_to_date(target_issue)
        history = full.iloc[:index].reset_index(drop=True)
        ranking, special_ranking = _rank_draws(draws[:index], regular_model, special_pack)
        days[target_day.isoformat()] = _assemble(
            history,
            ranking,
            special_ranking,
            target_day=target_day,
            full=full,
            actual=_actual_draw(full, target_issue),
            special_model="梯度提升树 + 逻辑回归",
            steps=1,
        )

    current = np.array(draws, copy=True)
    for step in range(1, future_days + 1):
        ranking, special_ranking = _rank_draws(current, regular_model, special_pack)
        target_day = last_day + timedelta(days=step)
        days[target_day.isoformat()] = _assemble(
            full,
            ranking,
            special_ranking,
            target_day=target_day,
            full=full,
            actual=None,
            special_model="梯度提升树 + 逻辑回归",
            steps=step,
        )
        current = np.vstack([current, _synthetic_draw(ranking, special_ranking)])

    ordered = sorted(days)
    today = today or date.today()
    default_date = today.isoformat() if today.isoformat() in days else (last_day + timedelta(days=1)).isoformat()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "default_date": default_date,
        "selectable_from": ordered[0],
        "selectable_to": ordered[-1],
        "days": days,
    }


def main() -> None:
    book = build_book()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(book, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUT}  {len(book['days'])} 天  默认 {book['default_date']}")


if __name__ == "__main__":
    main()
