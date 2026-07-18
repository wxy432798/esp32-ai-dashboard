#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def main() -> int:
    repo_dir = Path(__file__).resolve().parents[1]
    python_bin = os.environ.get("PYTHON_BIN", sys.executable)
    source = os.environ.get("SOURCE", "http://107.172.147.113:8787")
    prefix = os.environ.get("PREFIX", "render")
    env_file = os.environ.get("ENV_FILE", str(Path.home() / ".esp32-dashboard-oss.env"))

    sys.path.insert(0, str(repo_dir / "server"))
    sys.path.insert(0, str(repo_dir))
    from renderer import ensure_rendered_frame
    from tools.publish_eink_to_oss import _frame_info, _load_env_file, _put_object

    usage_result = subprocess.run([python_bin, str(repo_dir / "tools" / "mac_usage_reporter.py")], check=False)
    if usage_result.returncode != 0:
        print(
            f"warning: usage reporter failed with exit code {usage_result.returncode}; "
            "rendering with the latest server-side usage snapshot",
            file=sys.stderr,
        )

    with urllib.request.urlopen(source.rstrip("/") + "/api/eink-dashboard", timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8") or "{}")
    _ensure_weather_trend(payload)

    refresh = int(payload.get("refresh_interval") or payload.get("refresh_interval_sec") or 300)
    manifest = ensure_rendered_frame(payload, refresh, force=True)
    frame = Path(manifest["cache"]["bin"]).read_bytes()
    png = Path(manifest["cache"]["png"]).read_bytes()

    env_path = Path(env_file).expanduser()
    _load_env_file(env_path)
    endpoint = os.environ.get("OSS_ENDPOINT") or f"https://{os.environ.get('OSS_BUCKET', 'claudecodesapi')}.{os.environ.get('OSS_REGION', 'oss-cn-chengdu')}.aliyuncs.com"
    bucket = os.environ.get("OSS_BUCKET", "claudecodesapi")
    access_key_id = os.environ.get("OSS_ACCESS_KEY_ID", "").strip()
    access_key_secret = os.environ.get("OSS_ACCESS_KEY_SECRET", "").strip()
    if not access_key_id or not access_key_secret:
        raise RuntimeError(f"missing OSS credentials in {env_path}")

    public_manifest = {key: value for key, value in manifest.items() if key != "cache"}
    public_manifest["url"] = f"/{prefix}/eink.bin"
    public_manifest["png_url"] = f"/{prefix}/eink.png"
    public_manifest["oss_endpoint"] = endpoint
    public_manifest.update(_frame_info(frame))
    manifest_bytes = json.dumps(public_manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    objects = [
        (f"{prefix}/eink.bin", frame, "application/octet-stream"),
        (f"{prefix}/eink.png", png, "image/png"),
        (f"{prefix}/manifest.json", manifest_bytes, "application/json; charset=utf-8"),
    ]
    for key, data, content_type in objects:
        _put_object(endpoint, bucket, key, data, content_type, access_key_id, access_key_secret, True, 30)
        print(f"uploaded {endpoint}/{key} ({len(data)} bytes)")

    print(json.dumps({
        "manifest": f"{endpoint}/{prefix}/manifest.json",
        "frame": f"{endpoint}/{prefix}/eink.bin",
        "png": f"{endpoint}/{prefix}/eink.png",
        "crc32": public_manifest.get("crc32"),
        "bytes": public_manifest.get("bytes"),
        "source": "local-render",
    }, ensure_ascii=False, indent=2))
    return 0


def _ensure_weather_trend(payload: dict) -> None:
    weather = payload.get("weather")
    if not isinstance(weather, dict) or weather.get("trend"):
        return
    lat = os.environ.get("WEATHER_LAT", "30.5728")
    lon = os.environ.get("WEATHER_LON", "104.0668")
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code",
        "hourly": "temperature_2m",
        "forecast_days": 2,
        "wind_speed_unit": "ms",
        "timezone": "auto",
    })
    try:
        with urllib.request.urlopen(f"https://api.open-meteo.com/v1/forecast?{params}", timeout=8) as response:
            data = json.loads(response.read().decode("utf-8") or "{}")
    except Exception:
        return
    current_time = str(data.get("current", {}).get("time") or "")
    hourly = data.get("hourly") if isinstance(data.get("hourly"), dict) else {}
    times = hourly.get("time") if isinstance(hourly.get("time"), list) else []
    temps = hourly.get("temperature_2m") if isinstance(hourly.get("temperature_2m"), list) else []
    start = times.index(current_time) if current_time in times else 0
    trend = [round(float(v), 1) for v in temps[start:start + 8] if isinstance(v, (int, float))]
    if len(trend) >= 2:
        weather["trend"] = trend


if __name__ == "__main__":
    raise SystemExit(main())
