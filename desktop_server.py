"""在本机打开完整网页，并提供更新训练接口。"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from ml.data import ROOT
from ml.export_forecasts import OUT, build_book
from ml.next_reference import DEFAULT_MODEL_DIR
from ml.run_train import train_and_save
from ml.web_prediction import _PREPARED
from scripts.update_newam6hc import update_draws

DATA_FILES = {
    "newam6hc_5y_verified.csv",
    "am6hc_5y_verified.csv",
    "macau6hc_168_verified.csv",
    "newam6hc_5y.csv",
    "am6hc_5y.csv",
    "macau6hc_168.csv",
    "model_benchmark.csv",
    "model_benchmark.json",
    "train_report.json",
    "next_reference.json",
    "prediction_reference.json",
    "forecasts.json",
    "regular_benchmark.json",
}
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}
_JOB = threading.Lock()


def web_root() -> Path:
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "web"
    if (bundled / "index.html").is_file():
        return bundled
    return ROOT / "web" / "dist"


def _inside(root: Path, relative: str) -> Path | None:
    if not relative or relative.startswith(("/", "\\")) or ".." in Path(relative).parts:
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


class AppHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/api/desktop":
            self._send_json({"desktop": True})
            return
        if path.startswith("/data/"):
            self._send_data(path.removeprefix("/data/"))
            return
        self._send_page(path)

    def do_POST(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path != "/api/retrain":
            self._send_json({"error": "没有这个操作。"}, status=404)
            return
        if not _JOB.acquire(blocking=False):
            self._send_json({"error": "正在更新，请等这一次完成。"}, status=409)
            return
        try:
            fetched = update_draws()
            report = train_and_save(
                ROOT / "data" / "newam6hc_5y_verified.csv",
                DEFAULT_MODEL_DIR,
                ROOT / "data" / "train_report.json",
                save_fit="all",
            )
            _PREPARED.clear()
            book = build_book()
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps(book, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            top1 = report["metrics"]["test_ensemble"]["top1"]
            self._send_json({
                "changed": fetched["changed"],
                "before": fetched["before"],
                "after": fetched["after"],
                "default_date": book["default_date"],
                "test_top1": top1,
            })
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            self._send_json({"error": message}, status=500)
        finally:
            _JOB.release()

    def _send_data(self, name: str) -> None:
        if name not in DATA_FILES:
            self._send_json({"error": "没有这份数据。"}, status=404)
            return
        path = _inside(ROOT / "data", name)
        if path is None:
            self._send_json({"error": f"缺少 {name}"}, status=404)
            return
        self._send_file(path)

    def _send_page(self, path: str) -> None:
        root = web_root()
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        file_path = _inside(root, relative)
        if file_path is None and "." not in Path(relative).name:
            file_path = _inside(root, "index.html")
        if file_path is None:
            self.send_error(404)
            return
        self._send_file(file_path)

    def _send_file(self, path: Path) -> None:
        body = path.read_bytes()
        content_type = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def start_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}/"


def open_window() -> None:
    server, url = start_server()
    try:
        import webview

        webview.create_window("新澳门彩预测", url, width=1280, height=840, min_size=(980, 640))
        webview.start()
    finally:
        server.shutdown()
