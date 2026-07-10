#!/usr/bin/env python3
import argparse
import json
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class RelayState:
    upstream = "http://107.172.147.113"
    cache_ttl = 60
    manifest = None
    frame = b""
    fetched_at = 0.0


def _fetch(path, timeout=20):
    req = urllib.request.Request(
        RelayState.upstream + path,
        headers={
            "User-Agent": "local-eink-relay/1.0",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(), response.headers.get_content_type()


def _refresh_cache(force=False):
    now = time.time()
    if not force and RelayState.manifest and RelayState.frame and now - RelayState.fetched_at < RelayState.cache_ttl:
        return

    manifest_raw, _ = _fetch("/render/manifest.json", timeout=20)
    manifest = json.loads(manifest_raw.decode("utf-8"))
    frame_raw, _ = _fetch(manifest.get("url") or "/render/eink.bin", timeout=60)

    RelayState.manifest = manifest
    RelayState.frame = frame_raw
    RelayState.fetched_at = now


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, content_type, raw, extra_headers=None):
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("cache-control", "public, max-age=30")
        self.send_header("content-length", str(len(raw)))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path in ("/health", "/healthz"):
                self._send(200, "application/json", b'{"ok":true}')
                return

            if path == "/render/manifest.json":
                _refresh_cache()
                public = dict(RelayState.manifest)
                public["url"] = "/render/eink.bin"
                raw = json.dumps(public, ensure_ascii=False).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", raw)
                return

            if path == "/render/eink.bin":
                _refresh_cache()
                data = RelayState.frame
                query = parse_qs(parsed.query)
                if "offset" in query or "length" in query:
                    offset = max(0, int(query.get("offset", ["0"])[0]))
                    length = max(0, int(query.get("length", [str(len(data) - offset)])[0]))
                    chunk = data[offset:offset + length]
                    self._send(
                        206,
                        "application/octet-stream",
                        chunk,
                        {"content-range": f"bytes {offset}-{offset + len(chunk) - 1}/{len(data)}"},
                    )
                    return
                self._send(200, "application/octet-stream", data)
                return

            self._send(404, "application/json", b'{"error":"not found"}')
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            raw = json.dumps({"error": "relay failed", "detail": str(exc)}).encode("utf-8")
            self._send(502, "application/json", raw)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--upstream", default="http://107.172.147.113")
    parser.add_argument("--cache-ttl", type=int, default=60)
    args = parser.parse_args()

    RelayState.upstream = args.upstream.rstrip("/")
    RelayState.cache_ttl = args.cache_ttl

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Local e-ink relay: http://{args.host}:{args.port} -> {RelayState.upstream}")
    server.serve_forever()


if __name__ == "__main__":
    main()
