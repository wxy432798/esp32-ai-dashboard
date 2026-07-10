#!/usr/bin/env python3
import argparse
import getpass
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ENDPOINT = "http://107.172.147.113:8787/api/usage"
DEFAULT_SOURCE = Path.home() / ".esp32-dashboard-usage.json"
DEFAULT_KEY_FILE = Path.home() / ".esp32-dashboard-admin-key"
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_KEYCHAIN_SERVICE = "Claude Code-credentials"
CLAUDE_DEFAULT_CONFIG_DIR = Path.home() / ".claude"
CLAUDE_PROBE_MODEL = "claude-haiku-4-5-20251001"


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


def _extract_claude_access_token(blob: str) -> str:
    blob = blob.strip()
    if not blob:
        return ""
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        if isinstance(data.get("accessToken"), str):
            return data["accessToken"]
        for value in data.values():
            if isinstance(value, dict) and isinstance(value.get("accessToken"), str):
                return value["accessToken"]
    match = re.search(r'"accessToken"\s*:\s*"([^"]+)"', blob)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9_\-.~+/=]{20,}", blob):
        return blob
    return ""


def _read_claude_keychain_token() -> str:
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                CLAUDE_KEYCHAIN_SERVICE,
                "-a",
                getpass.getuser(),
                "-w",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return _extract_claude_access_token(result.stdout)


def _read_claude_file_token(config_dir: Path = CLAUDE_DEFAULT_CONFIG_DIR) -> str:
    credentials = config_dir.expanduser() / ".credentials.json"
    try:
        return _extract_claude_access_token(credentials.read_text(encoding="utf-8"))
    except OSError:
        return ""


def _read_claude_token() -> str:
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    if config_dir:
        token = _read_claude_file_token(Path(config_dir))
        if token:
            return token
    token = _read_claude_file_token()
    if token:
        return token
    if sys.platform == "darwin":
        return _read_claude_keychain_token()
    return ""


def _percent_from_utilization(value: str) -> int:
    try:
        return max(0, min(100, int(round(float(value) * 100))))
    except (TypeError, ValueError):
        return 0


def _minutes_until_epoch(value: str) -> int:
    try:
        seconds = float(value) - time.time()
    except (TypeError, ValueError):
        return 0
    return max(0, int(round(seconds / 60.0)))


def _format_minutes(minutes: int) -> str:
    if minutes <= 0:
        return "0m"
    days, rem = divmod(minutes, 1440)
    hours, mins = divmod(rem, 60)
    if days:
        return f"{days}d{hours}h"
    if hours:
        return f"{hours}h{mins}m"
    return f"{mins}m"


def _fetch_claude_usage(timeout: int) -> dict[str, Any] | None:
    token = _read_claude_token()
    if not token:
        return None

    raw = json.dumps({
        "model": CLAUDE_PROBE_MODEL,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "hi"}],
    }).encode("utf-8")
    request = urllib.request.Request(
        CLAUDE_API_URL,
        data=raw,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "oauth-2025-04-20",
            "Content-Type": "application/json",
            "User-Agent": "claude-code/2.1.5",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            headers = response.headers
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None

    def header(name: str, default: str = "0") -> str:
        return headers.get(name, default)

    if headers.get("anthropic-ratelimit-unified-5h-utilization"):
        session_percent = _percent_from_utilization(header("anthropic-ratelimit-unified-5h-utilization"))
        weekly_percent = _percent_from_utilization(header("anthropic-ratelimit-unified-7d-utilization"))
        session_reset = _minutes_until_epoch(header("anthropic-ratelimit-unified-5h-reset"))
        weekly_reset = _minutes_until_epoch(header("anthropic-ratelimit-unified-7d-reset"))
        status = header("anthropic-ratelimit-unified-5h-status", "unknown")
        used_today = "5h session"
    else:
        session_percent = _percent_from_utilization(header("anthropic-ratelimit-unified-overage-utilization"))
        weekly_percent = 0
        session_reset = _minutes_until_epoch(header("anthropic-ratelimit-unified-overage-reset"))
        weekly_reset = 0
        status = header("anthropic-ratelimit-unified-status", "unknown")
        used_today = "overage"

    return {
        "daily_percent": session_percent,
        "weekly_percent": weekly_percent,
        "daily_reset": _format_minutes(session_reset),
        "weekly_reset": _format_minutes(weekly_reset),
        "model": "Claude",
        "requests_today": "N/A",
        "used_today": used_today,
        "status": status,
        "source": "claude-code-headers",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


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


def _payload(source: Path, auto_claude: bool, timeout: int) -> dict[str, Any]:
    data = _read_json(source)
    payload: dict[str, Any] = {}
    for agent in ("claude", "codex"):
        block = data.get(agent)
        if isinstance(block, dict):
            block = dict(block)
            block.setdefault("updated_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
            payload[agent] = block
    if auto_claude:
        claude = _fetch_claude_usage(timeout)
        if claude:
            payload["claude"] = claude
        else:
            print("Claude auto probe unavailable; using source JSON", file=sys.stderr)
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
    parser.add_argument("--auto-claude", dest="auto_claude", action="store_true", default=True,
                        help="probe Claude Code rate-limit headers and override the claude block")
    parser.add_argument("--no-auto-claude", dest="auto_claude", action="store_false",
                        help="do not probe Claude; only report the source JSON")
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

    payload = _payload(source, args.auto_claude, args.timeout)
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
