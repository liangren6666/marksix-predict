"""新澳门彩期号与公历互转。每年期号从 1 连续编到当年最后一天。"""

from __future__ import annotations

from datetime import date, timedelta


def date_to_issue(day: date) -> int:
    return day.year * 1000 + day.timetuple().tm_yday


def issue_to_date(issue: int) -> date:
    year, seq = divmod(int(issue), 1000)
    if year < 1 or seq < 1:
        raise ValueError(f"期号无效: {issue}")
    try:
        day = date(year, 1, 1) + timedelta(days=seq - 1)
    except OverflowError as exc:
        raise ValueError(f"期号无效: {issue}") from exc
    if day.year != year:
        raise ValueError(f"期号 {issue} 超出 {year} 年的天数")
    return day


def next_issue(issue: int) -> int:
    return date_to_issue(issue_to_date(issue) + timedelta(days=1))
