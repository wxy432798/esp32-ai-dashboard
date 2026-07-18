import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
USAGE_DIR = ROOT / "data" / "state" / "usage"
VALID_AGENTS = {"claude", "codex"}


def _default_usage(agent: str) -> dict:
    return {
        "daily_percent": 0,
        "weekly_percent": 0,
        "daily_reset": "N/A",
        "weekly_reset": "N/A",
        "model": "N/A",
        "requests_today": "N/A",
        "used_today": "N/A",
        "status": "not_configured",
        "source": agent,
    }


def _load_json_file(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _state_usage_path(agent: str) -> Path:
    if agent not in VALID_AGENTS:
        raise ValueError(f"unknown usage agent: {agent}")
    return USAGE_DIR / f"{agent}.json"


def _load_state_usage(agent: str) -> dict | None:
    path = _state_usage_path(agent)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_ai_usage(agent: str, usage: dict) -> dict:
    """Persist one display-level usage block for a personal subscription.

    Personal Claude/ChatGPT/Codex subscriptions do not expose a stable admin
    usage API, so the dashboard accepts a small user-reported block instead.
    """

    if not isinstance(usage, dict):
        raise ValueError("usage must be a JSON object")
    path = _state_usage_path(agent)
    USAGE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(usage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return usage


def get_ai_usage(agent: str) -> dict:
    """Return the display-level usage block for claude or codex.

    This supports:

    - CLAUDE_USAGE_JSON=/path/to/file.json
    - CODEX_USAGE_JSON=/path/to/file.json
    - data/state/usage/claude.json and data/state/usage/codex.json
    - fallback to an explicit N/A block, never mock usage
    """

    env_key = "CLAUDE_USAGE_JSON" if agent == "claude" else "CODEX_USAGE_JSON"
    override = os.environ.get(env_key)
    if override:
        data = _load_json_file(override)
        return data.get(agent, data)
    state_usage = _load_state_usage(agent)
    if state_usage is not None:
        return state_usage
    return _default_usage(agent)
