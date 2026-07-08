#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from providers.ai_usage import get_ai_usage
from providers.system_metrics import get_server_status
from providers.weather import get_weather
from state_store import add_todo, delete_todo, load_note, load_todos, save_note, set_todo_done


DEFAULT_REFRESH_SEC = 300


class DashboardHTTPServer(ThreadingHTTPServer):
    def server_bind(self):
        self.socket.bind(self.server_address)
        self.server_name = self.server_address[0]
        self.server_port = self.server_address[1]


def _usage_percent(block):
    if isinstance(block, dict):
        for key in ("daily_percent", "used_percent", "percent"):
            value = block.get(key)
            if isinstance(value, (int, float)):
                return int(value)
    if isinstance(block, (int, float)):
        return int(block)
    return -1


def dashboard_payload(refresh_interval_sec=DEFAULT_REFRESH_SEC):
    server = get_server_status()
    claude = get_ai_usage("claude")
    codex = get_ai_usage("codex")
    todos = load_todos(limit=7)
    return {
        "refresh_interval_sec": refresh_interval_sec,
        "refresh_interval": refresh_interval_sec,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "claude": claude,
        "codex": codex,
        "ai": {
            "claude": -1,
            "codex": _usage_percent(codex),
        },
        "online": server.get("online", True),
        "cpu": server.get("cpu", -1),
        "ram": server.get("ram", -1),
        "disk": server.get("disk", -1),
        "load_avg": str(server.get("load_avg", "")),
        "uptime": server.get("uptime", ""),
        "server": server,
        "weather": get_weather(),
        "todos": len(todos),
        "todo_items": todos,
        "todo_count": len(todos),
        "note": load_note(),
    }


class Handler(BaseHTTPRequestHandler):
    refresh_interval_sec = DEFAULT_REFRESH_SEC
    esp32_api_key = ""

    def _authorized(self):
        if not self.esp32_api_key:
            return True
        auth = self.headers.get("authorization") or ""
        key = self.headers.get("x-api-key") or ""
        if auth.lower().startswith("bearer "):
            key = auth[7:]
        return key.strip() == self.esp32_api_key

    def _json(self, status, body):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self):
        length = int(self.headers.get("content-length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/health", "/healthz"):
            self._json(200, {"ok": True})
            return
        if path == "/api/eink-dashboard":
            if not self._authorized():
                self._json(401, {"error": "missing or invalid api key"})
                return
            self._json(200, dashboard_payload(self.refresh_interval_sec))
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self._read_json()
            if path == "/api/todo":
                action = data.get("action")
                if action == "add":
                    items = add_todo(str(data.get("text") or "").strip(), str(data.get("due") or "").strip())
                elif action == "done":
                    items = set_todo_done(int(data.get("index")), True)
                elif action == "undone":
                    items = set_todo_done(int(data.get("index")), False)
                elif action == "del":
                    items = delete_todo(int(data.get("index")))
                else:
                    self._json(400, {"error": "unknown todo action"})
                    return
                self._json(200, {"ok": True, "todos": items[:7]})
                return
            if path == "/api/note":
                save_note(data.get("note", ""))
                self._json(200, {"ok": True, "note": load_note()})
                return
            self._json(404, {"error": "not found"})
        except Exception as exc:
            self._json(400, {"error": str(exc)})

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--refresh", type=int, default=DEFAULT_REFRESH_SEC)
    args = parser.parse_args()

    Handler.refresh_interval_sec = args.refresh
    Handler.esp32_api_key = os.environ.get("ESP32_API_KEY", "").strip()
    server = DashboardHTTPServer((args.host, args.port), Handler)
    print(f"E-ink dashboard backend: http://{args.host}:{args.port}/api/eink-dashboard")
    server.serve_forever()


if __name__ == "__main__":
    main()
