"""新澳门彩预测的桌面窗口。"""

from __future__ import annotations

import threading
import tkinter as tk
from datetime import date, timedelta
from tkinter import font as tkfont

from ml.web_prediction import build_prediction, parse_day


BG = "#14171c"
PANEL = "#1c2128"
TEXT = "#e7ecf3"
MUTED = "#8b97a8"
GOLD = "#f0c27a"
GOLD_BG = "#3c2c18"
BLUE = "#9ec1ee"
BLUE_BG = "#24344c"
ACCENT = "#e7b56a"
DANGER = "#ffb4b8"


class PredictorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.busy = False
        self.payload = None
        root.title("新澳门彩预测")
        root.configure(bg=BG)
        root.minsize(860, 560)
        root.geometry("980x640")
        self.family = "Microsoft YaHei UI"
        self.number_font = tkfont.Font(family="Consolas", size=14, weight="bold")
        self.title_font = tkfont.Font(family=self.family, size=20, weight="bold")
        self.body_font = tkfont.Font(family=self.family, size=10)
        self.small_font = tkfont.Font(family=self.family, size=9)

        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=22, pady=(18, 8))
        tk.Label(header, text="新澳门彩预测", bg=BG, fg=TEXT, font=self.title_font).pack(side="left")

        controls = tk.Frame(root, bg=BG)
        controls.pack(fill="x", padx=22)
        tk.Label(controls, text="预测日期", bg=BG, fg=MUTED, font=self.small_font).pack(side="left")
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.date_entry = tk.Entry(
            controls, textvariable=self.date_var, width=12, bg=PANEL, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=self.body_font,
        )
        self.date_entry.pack(side="left", padx=(8, 8), ipady=6)
        self.date_entry.bind("<Return>", lambda _event: self.generate())
        self.prev_button = self._button(controls, "前一天", lambda: self.shift(-1))
        self.next_button = self._button(controls, "后一天", lambda: self.shift(1))
        self.run_button = self._button(controls, "生成预测", self.generate, primary=True)
        self.status = tk.Label(controls, text="", bg=BG, fg=MUTED, font=self.small_font)
        self.status.pack(side="right")

        self.issue_label = tk.Label(root, text="", bg=BG, fg=MUTED, font=self.body_font, anchor="w")
        self.issue_label.pack(fill="x", padx=22, pady=(10, 0))

        self.panel = tk.Frame(root, bg=PANEL, highlightthickness=1, highlightbackground="#2c333d")
        self.panel.pack(fill="both", expand=True, padx=22, pady=12)
        self.regular_labels = self._group(self.panel, "正码", "前 20 名", GOLD, GOLD_BG)
        self.special_labels = self._group(self.panel, "特码", "前 20 名", BLUE, BLUE_BG)
        self.note = tk.Label(
            self.panel, text="选择日期后点击「生成预测」。正码和特码各 20 个。",
            bg=PANEL, fg=MUTED, font=self.small_font, anchor="w", justify="left", wraplength=900,
        )
        self.note.pack(fill="x", padx=16, pady=(4, 14))
        self.generate()

    def _button(self, parent, text, command, primary=False):
        button = tk.Button(
            parent, text=text, command=command, relief="flat", cursor="hand2",
            bg=ACCENT if primary else PANEL, fg="#2a2116" if primary else TEXT,
            activebackground="#ffd59a" if primary else "#2a313b",
            activeforeground="#2a2116" if primary else TEXT,
            font=self.body_font, padx=12, pady=6,
        )
        button.pack(side="left", padx=(0, 8))
        return button

    def _group(self, parent, title, subtitle, color, background):
        box = tk.Frame(parent, bg=PANEL)
        box.pack(fill="x", padx=16, pady=(14, 4))
        heading = tk.Frame(box, bg=PANEL)
        heading.pack(fill="x")
        tk.Label(heading, text=title, bg=PANEL, fg=TEXT, font=self.body_font).pack(side="left")
        tk.Label(heading, text=subtitle, bg=PANEL, fg=MUTED, font=self.small_font).pack(side="left", padx=(8, 0))
        grid = tk.Frame(box, bg=PANEL)
        grid.pack(fill="x", pady=(8, 0))
        labels = []
        for index in range(20):
            label = tk.Label(
                grid, text="--", width=3, bg=background, fg=color,
                font=self.number_font, padx=4, pady=6,
            )
            label.grid(row=index // 10, column=index % 10, padx=4, pady=4, sticky="ew")
            labels.append(label)
        for column in range(10):
            grid.columnconfigure(column, weight=1)
        return labels

    def shift(self, days: int) -> None:
        try:
            current = parse_day(self.date_var.get().strip())
        except ValueError:
            current = date.today()
        self.date_var.set((current + timedelta(days=days)).isoformat())
        self.generate()

    def generate(self) -> None:
        if self.busy:
            return
        try:
            day = parse_day(self.date_var.get().strip())
        except ValueError as exc:
            self.note.configure(text=str(exc), fg=DANGER)
            return
        self.busy = True
        self.run_button.configure(text="正在计算…", state="disabled")
        self.status.configure(text="正在按这个日期计算")
        threading.Thread(target=self._calculate, args=(day,), daemon=True).start()

    def _calculate(self, day: date) -> None:
        try:
            payload = build_prediction(day=day)
            error = ""
        except Exception as exc:
            payload = None
            error = str(exc)
        self.root.after(0, lambda: self._show(payload, error))

    def _show(self, payload, error: str) -> None:
        self.busy = False
        self.run_button.configure(text="生成预测", state="normal")
        if error or not payload:
            self.status.configure(text="")
            self.note.configure(text=error or "计算失败。", fg=DANGER)
            return
        self.payload = payload
        target = payload["target"]
        last = payload["last_draw"]
        self.issue_label.configure(
            text=f"第 {target['issue']} 期 · 数据截至 {last['issue']} 期（{last['date']}）"
        )
        self._fill(self.regular_labels, payload["regular"]["picks"], payload.get("actual"), "regular")
        self._fill(self.special_labels, payload["special"]["picks"], payload.get("actual"), "special")
        self.note.configure(text=payload["note"], fg=MUTED)
        self.status.configure(text="已更新")

    def _fill(self, labels, picks, actual, kind: str) -> None:
        hits = set()
        if actual:
            hits = {actual["special"]} if kind == "special" else set(actual["regular"])
        for label, number in zip(labels, picks):
            label.configure(text=f"{int(number):02d}")
            if int(number) in hits:
                label.configure(highlightthickness=2, highlightbackground=TEXT)
            else:
                label.configure(highlightthickness=0)


def run() -> None:
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    PredictorApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()
