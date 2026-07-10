import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


def get_weather() -> dict:
    """Return display-level weather.

    Sources:
    - WEATHER_JSON=/path/to/file.json can contain a weather block or dashboard.
    - WEATHER_LAT and WEATHER_LON use Open-Meteo without an API key.
    - If not configured, return N/A values instead of mock weather.
    """

    override = os.environ.get("WEATHER_JSON")
    if override:
        data = json.loads(Path(override).read_text(encoding="utf-8"))
        return data.get("weather", data)

    lat = os.environ.get("WEATHER_LAT")
    lon = os.environ.get("WEATHER_LON")
    if lat and lon:
        try:
            params = urllib.parse.urlencode({
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code",
                "wind_speed_unit": "ms",
                "timezone": "auto",
            })
            with urllib.request.urlopen(f"https://api.open-meteo.com/v1/forecast?{params}", timeout=8) as res:
                data = json.loads(res.read().decode("utf-8"))
            current = data.get("current", {})
            return {
                "temperature": current.get("temperature_2m", "N/A"),
                "humidity": current.get("relative_humidity_2m", "N/A"),
                "wind": _wind_direction(current.get("wind_direction_10m")),
                "wind_speed": _wind_speed(current.get("wind_speed_10m")),
                "condition": _weather_code(current.get("weather_code")),
                "source": "open-meteo",
            }
        except Exception as exc:
            return _unknown_weather(f"weather_error:{exc.__class__.__name__}")

    return _unknown_weather("not_configured")


def _unknown_weather(status: str) -> dict:
    return {
        "temperature": "N/A",
        "humidity": "N/A",
        "wind": "N/A",
        "wind_speed": "N/A",
        "condition": "N/A",
        "status": status,
    }


def _wind_speed(value):
    if isinstance(value, (int, float)):
        return f"{value:.1f}m/s"
    return "N/A"


def _wind_direction(degrees):
    if not isinstance(degrees, (int, float)):
        return "N/A"
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[int((degrees + 22.5) // 45) % 8]


def _weather_code(code):
    labels = {
        0: "Clear",
        1: "Mainly Clear",
        2: "Partly Cloudy",
        3: "Cloudy",
        45: "Fog",
        48: "Fog",
        51: "Drizzle",
        53: "Drizzle",
        55: "Drizzle",
        61: "Rain",
        63: "Rain",
        65: "Rain",
        71: "Snow",
        73: "Snow",
        75: "Snow",
        80: "Showers",
        81: "Showers",
        82: "Showers",
        95: "Thunder",
    }
    if isinstance(code, (int, float)):
        return labels.get(int(code), "N/A")
    return "N/A"
