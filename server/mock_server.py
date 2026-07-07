#!/usr/bin/env python3
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOCK_JSON = ROOT / "data" / "mock" / "dashboard.json"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?", 1)[0] != "/api/eink-dashboard":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return
        body = MOCK_JSON.read_bytes()
        json.loads(body.decode("utf-8"))
        self.send_response(200)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Mock dashboard API: http://{args.host}:{args.port}/api/eink-dashboard")
    server.serve_forever()


if __name__ == "__main__":
    main()
