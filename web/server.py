#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.demo import DemoState

STATIC = Path(__file__).resolve().parent / "static"
DIAGRAM_PNG = ROOT / "docs" / "gambar" / "use-case.png"
DIAGRAM_PDF = ROOT / "docs" / "gambar" / "use-case.pdf"

STATE = DemoState()


class Handler(BaseHTTPRequestHandler):
    server_version = "SeBattWeb/1.0"

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, content_type: str | None = None) -> None:
        if not path.is_file():
            self._json({"ok": False, "message": "File tidak ditemukan."}, 404)
            return
        data = path.read_bytes()
        ctype = content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        if length > 1_000_000:
            raise ValueError("Payload terlalu besar.")
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("JSON tidak valid.") from exc
        if not isinstance(value, dict):
            raise ValueError("Payload harus berupa objek JSON.")
        return value

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/state":
            self._json(STATE.state())
            return
        if path in ("/", "/index.html"):
            self._file(STATIC / "index.html", "text/html; charset=utf-8")
            return
        if path == "/diagram":
            self._file(STATIC / "diagram.html", "text/html; charset=utf-8")
            return
        if path == "/app.js":
            self._file(STATIC / "app.js", "text/javascript; charset=utf-8")
            return
        if path == "/style.css":
            self._file(STATIC / "style.css", "text/css; charset=utf-8")
            return
        if path == "/use-case.png":
            self._file(DIAGRAM_PNG, "image/png")
            return
        if path == "/use-case.pdf":
            self._file(DIAGRAM_PDF, "application/pdf")
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        self._json({"ok": False, "message": "Halaman tidak ditemukan."}, 404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._read_json()
        except ValueError as exc:
            self._json({"ok": False, "message": str(exc)}, 400)
            return

        try:
            if path == "/api/record":
                mv = int(body.get("mv", 0))
                self._json({"ok": True, "state": STATE.record(mv)})
                return
            if path == "/api/swap":
                self._json({"ok": True, "state": STATE.swap()})
                return
            if path == "/api/attack/delete":
                result = STATE.attack_delete()
                self._json(result, 200 if result.get("ok") else 400)
                return
            if path == "/api/attack/tamper":
                result = STATE.attack_tamper()
                self._json(result, 200 if result.get("ok") else 400)
                return
            if path == "/api/restore":
                self._json({"ok": True, "state": STATE.restore()})
                return
            if path == "/api/reset":
                self._json({"ok": True, "state": STATE.reset()})
                return
            if path == "/api/unlock":
                self._json({"ok": True, "state": STATE.unlock()})
                return
            if path == "/api/power-cycle":
                self._json({"ok": True, "state": STATE.power_cycle()})
                return
        except (TypeError, ValueError) as exc:
            self._json({"ok": False, "message": str(exc)}, 400)
            return

        self._json({"ok": False, "message": "Endpoint tidak ditemukan."}, 404)

    def log_message(self, fmt: str, *args) -> None:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Dashboard web stasiun SeBatt")
    parser.add_argument("--host", default="127.0.0.1", help="Alamat bind (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port HTTP (default 8000)")
    parser.add_argument("--open", action="store_true", help="Buka browser otomatis")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True

    print("SeBatt Station Dashboard")
    print(f"  {url}")
    print("  Mode simulasi. Tekan Ctrl+C untuk berhenti.")

    if args.open:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBerhenti.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
