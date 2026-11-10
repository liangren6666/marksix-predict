"""六合彩类彩种：55128 / 168 抓取、解析与校验共用库。"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE_55128 = "https://m.55128.cn"
BASE_168 = "https://168yh.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
COLOR_RE = re.compile(r"kj-(red|blue|green)")
PAGE_RE = re.compile(r"第\s*\d+\s*/\s*(\d+)\s*页")


@dataclass(frozen=True)
class MarksixKind:
    """一种可独立使用的开奖产品线。"""

    key: str
    display_name: str
    api_name_55128: str | None = None
    game_168: int | None = None

    @property
    def history_url_template(self) -> str | None:
        if not self.api_name_55128:
            return None
        return f"{BASE_55128}/kjh/history_{self.api_name_55128}.aspx?year={{year}}"

    def detail_url(self, issue: int) -> str | None:
        if not self.api_name_55128:
            return None
        return f"{BASE_55128}/kjh/{self.api_name_55128}-kjjg-{issue}.htm"


NEW_AM6HC = MarksixKind(
    key="newam6hc",
    display_name="新澳门彩",
    api_name_55128="newam6hc",
    game_168=301,
)
AM6HC = MarksixKind(
    key="am6hc",
    display_name="澳门彩",
    api_name_55128="am6hc",
    game_168=None,
)
MACAU6HC_168 = MarksixKind(
    key="macau6hc_168",
    display_name="澳门六合彩(168)",
    api_name_55128=None,
    game_168=300,
)

KINDS: dict[str, MarksixKind] = {
    k.key: k for k in (NEW_AM6HC, AM6HC, MACAU6HC_168)
}


def fetch_text(url: str, timeout: float = 60) -> str:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def row_balls(row: dict) -> list[int]:
    return [int(row[f"n{i}"]) for i in range(1, 7)] + [int(row["special"])]


def parse_item(item) -> dict | None:
    strong = item.select_one(".item-title strong")
    if not strong:
        return None
    issue = int(strong.get_text(strip=True))
    blocks = item.select(".kj-detailss > .kjh-wxs")
    if len(blocks) < 7:
        return None

    balls_meta = []
    for block in blocks:
        span = block.select_one("span")
        meta = block.select_one("p")
        if not span:
            continue
        classes = span.get("class") or []
        color = ""
        for c in classes:
            m = COLOR_RE.search(c)
            if m:
                color = m.group(1)
                break
        num = int(span.get_text(strip=True))
        zodiac, wuxing = "", ""
        if meta:
            parts = meta.get_text(strip=True).split("/")
            if len(parts) == 2:
                zodiac, wuxing = parts
        balls_meta.append(
            {"num": num, "color": color, "zodiac": zodiac, "wuxing": wuxing}
        )

    regular = balls_meta[:6]
    special = balls_meta[6]
    return {
        "issue": issue,
        "year": issue // 1000,
        "seq": issue % 1000,
        "lottery": "",
        "nums": [b["num"] for b in regular],
        "special": special["num"],
        "colors": [b["color"] for b in regular] + [special["color"]],
        "zodiacs": [b["zodiac"] for b in regular] + [special["zodiac"]],
        "wuxings": [b["wuxing"] for b in regular] + [special["wuxing"]],
        "open_time": "",
    }


def parse_55128_year_html(html: str, lottery_key: str = "") -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for item in soup.select("section.item-wrapper .item"):
        row = parse_item(item)
        if row:
            row["lottery"] = lottery_key
            rows.append(row)
    return rows


def parse_55128_year_map(html: str) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for row in parse_55128_year_html(html):
        out[row["issue"]] = row["nums"] + [row["special"]]
    return out


def fetch_55128_years(kind: MarksixKind) -> list[int]:
    if not kind.api_name_55128:
        return []
    raw = fetch_text(f"{BASE_55128}/Kjh/KjhHistoryYear?name={kind.api_name_55128}")
    return json.loads(raw)


def fetch_55128_year(kind: MarksixKind, year: int) -> list[dict]:
    if not kind.history_url_template:
        raise ValueError(f"{kind.key} 无 55128 历史页")
    url = kind.history_url_template.format(year=year)
    html = fetch_text(url)
    return parse_55128_year_html(html, kind.key)


def parse_55128_detail_html(html: str) -> list[int]:
    soup = BeautifulSoup(html, "html.parser")
    balls = []
    for block in soup.select(".kj-detailss > .kjh-wxs"):
        span = block.select_one("span")
        if span:
            balls.append(int(span.get_text(strip=True)))
    return balls


def fetch_55128_detail(kind: MarksixKind, issue: int) -> list[int]:
    url = kind.detail_url(issue)
    if not url:
        raise ValueError(f"{kind.key} 无 55128 详情页")
    return parse_55128_detail_html(fetch_text(url))


def parse_168_max_pages(html: str) -> int:
    toolbar = BeautifulSoup(html, "html.parser").select_one(".history-toolbar span")
    if not toolbar:
        return 1
    m = PAGE_RE.search(toolbar.get_text())
    return int(m.group(1)) if m else 1


def parse_168_history_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for tr in soup.select("#history tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        issue = int(tds[1].get_text(strip=True))
        balls = [int(s.get_text(strip=True)) for s in tds[2].select(".ball")]
        if len(balls) != 7:
            continue
        open_time = tds[0].get_text(strip=True) or ""
        rows.append(
            {
                "issue": issue,
                "year": issue // 1000,
                "seq": issue % 1000,
                "lottery": "",
                "nums": balls[:6],
                "special": balls[6],
                "colors": [""] * 7,
                "zodiacs": [""] * 7,
                "wuxings": [""] * 7,
                "open_time": open_time,
            }
        )
    return rows


def fetch_168_history(kind: MarksixKind) -> list[dict]:
    if not kind.game_168:
        raise ValueError(f"{kind.key} 无 168 历史页")
    first_url = f"{BASE_168}/game/{kind.game_168}/"
    first_html = fetch_text(first_url, timeout=30)
    max_page = parse_168_max_pages(first_html)
    all_rows: list[dict] = []
    for page in range(1, max_page + 1):
        url = f"{BASE_168}/game/{kind.game_168}/?page={page}"
        html = first_html if page == 1 else fetch_text(url, timeout=30)
        batch = parse_168_history_html(html)
        if not batch and page > 1:
            break
        for row in batch:
            row["lottery"] = kind.key
        all_rows.extend(batch)
    by_issue: dict[int, dict] = {}
    for row in all_rows:
        by_issue[row["issue"]] = row
    return sorted(by_issue.values(), key=lambda r: r["issue"], reverse=True)


def fetch_168_history_map(game_id: int, max_page: int | None = None) -> dict[int, list[int]]:
    kind = MarksixKind("tmp", "", game_168=game_id)
    if max_page is None:
        first_html = fetch_text(f"{BASE_168}/game/{game_id}/", timeout=30)
        max_page = parse_168_max_pages(first_html)
    out: dict[int, list[int]] = {}
    for page in range(1, max_page + 1):
        url = f"{BASE_168}/game/{game_id}/?page={page}"
        html = fetch_text(url, timeout=30)
        for row in parse_168_history_html(html):
            out[row["issue"]] = row["nums"] + [row["special"]]
    return out


# 兼容旧接口
def fetch_55128_year_legacy(year: int) -> dict[int, list[int]]:
    return parse_55128_year_map(
        fetch_text(NEW_AM6HC.history_url_template.format(year=year))
    )


def fetch_168_history_pages(max_page: int = 15) -> dict[int, list[int]]:
    return fetch_168_history_map(301, max_page)


def fetch_55128_detail_legacy(issue: int) -> list[int]:
    return fetch_55128_detail(NEW_AM6HC, issue)


def load_csv(path: Path) -> dict[int, dict]:
    rows: dict[int, dict] = {}
    with path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            issue = int(row["issue"])
            rows[issue] = row
    return rows


def _join_meta(items: list[str]) -> str:
    if not items or not any(x.strip() for x in items):
        return ""
    return ",".join(items)


def save_csv(rows: list[dict], path: Path) -> None:
    fields = [
        "issue",
        "year",
        "seq",
        "lottery",
        "n1",
        "n2",
        "n3",
        "n4",
        "n5",
        "n6",
        "special",
        "colors",
        "zodiacs",
        "wuxings",
        "open_time",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "issue": r["issue"],
                    "year": r["year"],
                    "seq": r["seq"],
                    "lottery": r.get("lottery", ""),
                    "n1": r["nums"][0],
                    "n2": r["nums"][1],
                    "n3": r["nums"][2],
                    "n4": r["nums"][3],
                    "n5": r["nums"][4],
                    "n6": r["nums"][5],
                    "special": r["special"],
                    "colors": _join_meta(r.get("colors", [])),
                    "zodiacs": _join_meta(r.get("zodiacs", [])),
                    "wuxings": _join_meta(r.get("wuxings", [])),
                    "open_time": r.get("open_time", ""),
                }
            )


def save_verified_csv(rows: list[dict], path: Path) -> None:
    fields = [
        "issue",
        "year",
        "seq",
        "lottery",
        "n1",
        "n2",
        "n3",
        "n4",
        "n5",
        "n6",
        "special",
        "colors",
        "zodiacs",
        "wuxings",
        "open_time",
        "verify_status",
        "verify_sources",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def rows_to_verified_csv_dict(row: dict, status: str, sources: str) -> dict:
    return {
        "issue": row["issue"],
        "year": row["year"],
        "seq": row["seq"],
        "lottery": row.get("lottery", ""),
        "n1": row["nums"][0] if isinstance(row["nums"], list) else row["n1"],
        "n2": row["nums"][1] if isinstance(row["nums"], list) else row["n2"],
        "n3": row["nums"][2] if isinstance(row["nums"], list) else row["n3"],
        "n4": row["nums"][3] if isinstance(row["nums"], list) else row["n4"],
        "n5": row["nums"][4] if isinstance(row["nums"], list) else row["n5"],
        "n6": row["nums"][5] if isinstance(row["nums"], list) else row["n6"],
        "special": row["special"],
        "colors": ",".join(row["colors"]) if isinstance(row.get("colors"), list) else row.get("colors", ""),
        "zodiacs": ",".join(row["zodiacs"]) if isinstance(row.get("zodiacs"), list) else row.get("zodiacs", ""),
        "wuxings": ",".join(row["wuxings"]) if isinstance(row.get("wuxings"), list) else row.get("wuxings", ""),
        "open_time": row.get("open_time", ""),
        "verify_status": status,
        "verify_sources": sources,
    }
