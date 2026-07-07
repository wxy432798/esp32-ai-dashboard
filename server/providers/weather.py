import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MOCK_JSON = ROOT / "data" / "mock" / "dashboard.json"


def get_weather() -> dict:
    """Return display-level weather.

    Wire real weather API here later. If WEATHER_JSON points to a file, it can
    either contain the weather block directly or the full dashboard mock shape.
    """

    override = os.environ.get("WEATHER_JSON")
    if override:
        data = json.loads(Path(override).read_text(encoding="utf-8"))
        return data.get("weather", data)
    return json.loads(MOCK_JSON.read_text(encoding="utf-8"))["weather"]

