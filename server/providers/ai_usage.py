import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MOCK_JSON = ROOT / "data" / "mock" / "dashboard.json"


def _default_usage(agent: str) -> dict:
    mock = json.loads(MOCK_JSON.read_text(encoding="utf-8"))
    return mock[agent]


def _load_json_file(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_ai_usage(agent: str) -> dict:
    """Return the display-level usage block for claude or codex.

    Real API wiring belongs here. For now this supports:

    - CLAUDE_USAGE_JSON=/path/to/file.json
    - CODEX_USAGE_JSON=/path/to/file.json
    - fallback to data/mock/dashboard.json
    """

    env_key = "CLAUDE_USAGE_JSON" if agent == "claude" else "CODEX_USAGE_JSON"
    override = os.environ.get(env_key)
    if override:
        data = _load_json_file(override)
        return data.get(agent, data)
    return _default_usage(agent)

