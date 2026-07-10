#!/usr/bin/env python3
import argparse
import base64
import getpass
import json
import os
import re
import select
import shutil
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
CODEX_AUTH_FILE = Path.home() / ".codex" / "auth.json"
CODEX_RESET_CREDITS_URL = "https://chatgpt.com/backend-api/wham/rate-limit-reset-credits"
CODEX_APP_BUNDLE_CLI = "/Applications/Codex.app/Contents/Resources/codex"


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


def _jwt_payload(token: str) -> dict[str, Any]:
    parts = str(token or "").split(".")
    if len(parts) < 2:
        return {}
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = base64.urlsafe_b64decode(payload.encode("ascii"))
        parsed = json.loads(data.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, json.JSONDecodeError):
        return {}


def _read_codex_auth() -> dict[str, Any]:
    path = Path(os.environ.get("CODEX_AUTH_FILE", str(CODEX_AUTH_FILE))).expanduser()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _codex_tokens(auth: dict[str, Any]) -> dict[str, str]:
    tokens = auth.get("tokens") if isinstance(auth.get("tokens"), dict) else auth
    return {
        "access_token": str(tokens.get("access_token") or auth.get("access_token") or "").strip(),
        "id_token": str(tokens.get("id_token") or auth.get("id_token") or "").strip(),
    }


def _codex_account_id(id_token: str) -> str:
    payload = _jwt_payload(id_token)
    nested = payload.get("https://api.openai.com/auth") or payload.get("https://api.openai.com/profile") or {}
    if not isinstance(nested, dict):
        nested = {}
    return str(
        payload.get("chatgpt_account_id")
        or nested.get("chatgpt_account_id")
        or payload.get("sub")
        or ""
    ).strip()


def _parse_codex_reset_credits(data: dict[str, Any]) -> tuple[int, list[str]]:
    available = data.get("available_count", data.get("availableCount", 0))
    try:
        available_count = max(0, int(float(available)))
    except (TypeError, ValueError):
        available_count = 0

    now = time.time()
    expirations = []
    credits = data.get("credits") if isinstance(data.get("credits"), list) else []
    for credit in credits:
        if not isinstance(credit, dict):
            continue
        if str(credit.get("status", "")).lower() != "available":
            continue
        expires_at = credit.get("expires_at", credit.get("expiresAt"))
        try:
            expires_ts = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError):
            continue
        if expires_ts > now:
            expirations.append(datetime.fromtimestamp(expires_ts, timezone.utc).isoformat(timespec="seconds"))
    expirations.sort()
    return available_count, expirations


def _fetch_codex_usage(timeout: int) -> dict[str, Any] | None:
    rpc_usage = _fetch_codex_rpc_usage(timeout)
    if rpc_usage:
        return rpc_usage
    reset_credits = _fetch_codex_reset_credits(min(timeout, 4))
    if reset_credits:
        available_count = int(reset_credits.get("available_count") or 0)
        next_expires_at = reset_credits.get("next_expires_at")
        next_minutes = 0
        if next_expires_at:
            try:
                next_minutes = _minutes_until_epoch(str(datetime.fromisoformat(next_expires_at).timestamp()))
            except ValueError:
                next_minutes = 0
        return {
            "daily_percent": 0,
            "weekly_percent": 0,
            "daily_reset": _format_minutes(next_minutes) if next_expires_at else "N/A",
            "weekly_reset": "N/A",
            "model": "Codex",
            "requests_today": available_count,
            "used_today": f"{available_count} resets",
            "status": "credits",
            "reset_credits": reset_credits,
            "source": "codex-reset-credits",
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    return None


def _codex_command() -> str:
    explicit = os.environ.get("CODEX_COMMAND", "").strip()
    if explicit:
        return explicit
    bundled = Path(CODEX_APP_BUNDLE_CLI)
    if bundled.exists():
        return str(bundled)
    return shutil.which("codex") or "codex"


def _read_codex_rpc(timeout: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    command = _codex_command()
    deadline = time.time() + max(3, timeout)
    process = subprocess.Popen(
        [command, "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    def send(message: dict[str, Any]) -> None:
        if process.stdin is None:
            return
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    rate_limits = None
    account = None
    try:
        send({
            "id": 1,
            "method": "initialize",
            "params": {"clientInfo": {"name": "esp32-dashboard", "title": "ESP32 Dashboard", "version": "0.1"}},
        })
        send({"method": "initialized", "params": {}})
        send({"id": 2, "method": "account/rateLimits/read", "params": {}})
        send({"id": 3, "method": "account/read", "params": {}})

        while time.time() < deadline and (rate_limits is None or account is None):
            if process.stdout is None:
                break
            ready, _, _ = select.select([process.stdout], [], [], 0.25)
            if not ready:
                if process.poll() is not None:
                    break
                continue
            line = process.stdout.readline()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") == 2:
                rate_limits = message.get("result") if isinstance(message.get("result"), dict) else {}
            elif message.get("id") == 3:
                result = message.get("result") if isinstance(message.get("result"), dict) else {}
                account = result.get("account") if isinstance(result.get("account"), dict) else {}
        return rate_limits, account
    except (OSError, BrokenPipeError):
        return None, None
    finally:
        try:
            process.terminate()
            process.wait(timeout=1)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass


def _rate_limits_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    direct = result.get("rateLimits") if isinstance(result.get("rateLimits"), dict) else {}
    by_id = result.get("rateLimitsByLimitId") if isinstance(result.get("rateLimitsByLimitId"), dict) else {}
    codex = by_id.get("codex") if isinstance(by_id.get("codex"), dict) else {}
    if direct.get("primary") or direct.get("secondary"):
        return direct
    return codex


def _reset_from_epoch(value: Any) -> str:
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if raw > 20_000_000_000:
        raw = raw / 1000.0
    return _format_minutes(_minutes_until_epoch(str(raw)))


def _fetch_codex_rpc_usage(timeout: int) -> dict[str, Any] | None:
    result, account = _read_codex_rpc(timeout)
    if not result:
        return None
    snapshot = _rate_limits_snapshot(result)
    primary = snapshot.get("primary") if isinstance(snapshot.get("primary"), dict) else {}
    secondary = snapshot.get("secondary") if isinstance(snapshot.get("secondary"), dict) else {}
    if not primary and not secondary:
        return None

    def percent(window: dict[str, Any]) -> int:
        try:
            return max(0, min(100, int(round(float(window.get("usedPercent", window.get("used_percent", 0)))))))
        except (TypeError, ValueError):
            return 0

    plan = ""
    if isinstance(account, dict):
        plan = str(account.get("planType") or account.get("plan_type") or "").strip()
    if not plan:
        plan = str(snapshot.get("planType") or snapshot.get("plan_type") or "").strip()

    reached = snapshot.get("rateLimitReachedType") or snapshot.get("rate_limit_reached_type")
    return {
        "daily_percent": percent(primary),
        "weekly_percent": percent(secondary),
        "daily_reset": _reset_from_epoch(primary.get("resetsAt", primary.get("resets_at"))),
        "weekly_reset": _reset_from_epoch(secondary.get("resetsAt", secondary.get("resets_at"))),
        "model": "Codex",
        "requests_today": "N/A",
        "used_today": "5h session",
        "status": "limited" if reached else "ok",
        "account_label": plan,
        "source": "codex-app-server-rpc",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _fetch_codex_reset_credits(timeout: int) -> dict[str, Any] | None:
    auth = _read_codex_auth()
    tokens = _codex_tokens(auth)
    access_token = tokens["access_token"]
    if not access_token:
        return None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "esp32-dashboard-mac-usage-reporter/1.0",
        "openai-beta": "codex-1",
        "originator": "Codex Desktop",
    }
    account_id = _codex_account_id(tokens["id_token"])
    if account_id:
        headers["chatgpt-account-id"] = account_id

    request = urllib.request.Request(CODEX_RESET_CREDITS_URL, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8") or "{}")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    available_count, expirations = _parse_codex_reset_credits(data)
    return {
        "available_count": available_count,
        "next_expires_at": expirations[0] if expirations else None,
        "expirations": expirations,
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


def _payload(source: Path, auto_claude: bool, auto_codex: bool, timeout: int, skip_failed_auto: bool) -> dict[str, Any]:
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
            if skip_failed_auto and payload.get("claude", {}).get("source") not in ("claude-code-headers",):
                payload.pop("claude", None)
    if auto_codex:
        codex = _fetch_codex_usage(timeout)
        if codex:
            payload["codex"] = codex
        else:
            print("Codex auto probe unavailable; using source JSON", file=sys.stderr)
            if skip_failed_auto and payload.get("codex", {}).get("source") not in ("codex-app-server-rpc", "codex-reset-credits"):
                payload.pop("codex", None)
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
    parser.add_argument("--auto-codex", dest="auto_codex", action="store_true", default=True,
                        help="probe Codex reset credits and override the codex block")
    parser.add_argument("--no-auto-codex", dest="auto_codex", action="store_false",
                        help="do not probe Codex; only report the source JSON")
    parser.add_argument("--skip-failed-auto", action="store_true", default=True,
                        help="do not report template fallback blocks when an enabled auto probe fails")
    parser.add_argument("--no-skip-failed-auto", dest="skip_failed_auto", action="store_false",
                        help="report source JSON fallback blocks even when auto probes fail")
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

    try:
        payload = _payload(source, args.auto_claude, args.auto_codex, args.timeout, args.skip_failed_auto)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
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
