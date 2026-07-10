#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ENDPOINT = "http://107.172.147.113:8787/api/usage"
DEFAULT_SOURCE = Path.home() / ".esp32-dashboard-usage.json"
DEFAULT_KEY_FILE = Path.home() / ".esp32-dashboard-admin-key"


TEMPLATE = {
    "claude": {
        "daily_percent": 0,
        "weekly_percent": 0,
        "daily_reset": "N/A",
        "weekly_reset": "N/A",
        "model": "Claude",
        "requests_today": 0,
        "used_today": "personal",
        "status": "Active",
    },
    "codex": {
        "daily_percent": 0,
        "weekly_percent": 0,
        "daily_reset": "N/A",
        "weekly_reset": "N/A",
        "model": "Codex",
        "requests_today": 0,
        "used_today": "personal",
        "status": "Running",
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_template(path: Path) -> None:
    path.write_text(json.dumps(TEMPLATE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _admin_key(args: argparse.Namespace) -> str:
    if args.admin_key:
        return args.admin_key.strip()
    env_key = os.environ.get("ADMIN_API_KEY", "").strip()
    if env_key:
        return env_key
    key_file = Path(args.admin_key_file).expanduser()
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    return ""


def _payload(source: Path) -> dict[str, Any]:
    data = _read_json(source)
    payload: dict[str, Any] = {}
    for agent in ("claude", "codex"):
        block = data.get(agent)
        if isinstance(block, dict):
            block = dict(block)
            block.setdefault("updated_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
            payload[agent] = block
    if not payload:
        raise ValueError("source JSON must contain a claude and/or codex object")
    return payload


def _post(endpoint: str, admin_key: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=raw,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-API-Key": admin_key,
            "User-Agent": "esp32-dashboard-mac-usage-reporter/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return json.loads(body or "{}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Report personal Claude/Codex usage to the ESP32 dashboard backend.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="usage JSON file to read")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="dashboard backend /api/usage endpoint")
    parser.add_argument("--admin-key", default="", help="admin API key; prefer env or key file")
    parser.add_argument("--admin-key-file", default=str(DEFAULT_KEY_FILE), help="file containing ADMIN_API_KEY")
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--init", action="store_true", help="create a template source JSON and exit")
    parser.add_argument("--dry-run", action="store_true", help="print payload without posting")
    args = parser.parse_args()

    source = Path(args.source).expanduser()
    if args.init:
        if source.exists():
            print(f"exists: {source}")
            return 0
        _write_template(source)
        os.chmod(source, 0o600)
        print(f"created: {source}")
        return 0

    if not source.exists():
        print(f"missing source: {source}", file=sys.stderr)
        print(f"run: {sys.argv[0]} --init", file=sys.stderr)
        return 2

    payload = _payload(source)
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    key = _admin_key(args)
    if not key:
        print("missing admin key: set ADMIN_API_KEY or create ~/.esp32-dashboard-admin-key", file=sys.stderr)
        return 2

    try:
        response = _post(args.endpoint, key, payload, args.timeout)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"POST failed: HTTP {exc.code} {detail}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"POST failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(response, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
