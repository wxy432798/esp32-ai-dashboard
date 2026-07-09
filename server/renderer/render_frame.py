import html
import json
import os
import shutil
import struct
import subprocess
import threading
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "frontend" / "eink-dashboard.html"
CACHE_DIR = Path(os.environ.get("EINK_RENDER_CACHE_DIR", ROOT / "data" / "render_cache"))

WIDTH = 400
HEIGHT = 300
MAGIC = b"EINK3C01"
FORMAT = "eink3c-bin-v1"
_RENDER_LOCK = threading.Lock()


def _chrome_bin():
    configured = os.environ.get("CHROMIUM_BIN")
    if configured:
        return configured
    for candidate in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        found = shutil.which(candidate)
        if found:
            return found
    raise RuntimeError("Chromium is not installed or CHROMIUM_BIN is not set")


def _source_hash(payload):
    h = zlib.crc32(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    h = zlib.crc32(TEMPLATE.read_bytes(), h)
    return f"{h & 0xffffffff:08x}"


def _load_manifest():
    path = CACHE_DIR / "latest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _cache_valid(manifest, source_hash, max_age_sec):
    if not manifest:
        return False
    if manifest.get("source_hash") != source_hash:
        return False
    if not (CACHE_DIR / "latest.png").exists() or not (CACHE_DIR / "latest.bin").exists():
        return False
    generated_at = float(manifest.get("generated_at_epoch") or 0)
    return time.time() - generated_at < max_age_sec


def _write_render_html(payload):
    rendered = CACHE_DIR / "render.html"
    raw_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    template = TEMPLATE.read_text(encoding="utf-8")
    template = template.replace("__DASHBOARD_JSON__", raw_json)
    rendered.write_text(template, encoding="utf-8")
    return rendered


def _screenshot(rendered_html):
    raw_png = CACHE_DIR / "latest.raw.png"
    cmd = [
        _chrome_bin(),
        "--headless=new",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        "--no-sandbox",
        f"--window-size={WIDTH},{HEIGHT}",
        f"--screenshot={raw_png}",
        rendered_html.resolve().as_uri(),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    return raw_png


def _classify_pixel(r, g, b):
    if r > 130 and r > g * 1.25 and r > b * 1.25 and r - max(g, b) > 35:
        return "red"
    luminance = (299 * r + 587 * g + 114 * b) / 1000
    if luminance < 165:
        return "black"
    return "white"


def _set_bit(buffer, index):
    buffer[index // 8] |= 0x80 >> (index % 8)


def _quantize_and_pack(raw_png):
    image = Image.open(raw_png).convert("RGB")
    if image.size != (WIDTH, HEIGHT):
        image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

    black = bytearray(WIDTH * HEIGHT // 8)
    red = bytearray(WIDTH * HEIGHT // 8)
    preview = Image.new("RGB", (WIDTH, HEIGHT), "white")
    source = image.load()
    target = preview.load()

    for y in range(HEIGHT):
        for x in range(WIDTH):
            idx = y * WIDTH + x
            cls = _classify_pixel(*source[x, y])
            if cls == "black":
                _set_bit(black, idx)
                target[x, y] = (0, 0, 0)
            elif cls == "red":
                _set_bit(red, idx)
                target[x, y] = (210, 32, 24)
            else:
                target[x, y] = (255, 255, 255)

    payload = bytes(black) + bytes(red)
    crc = zlib.crc32(payload) & 0xffffffff
    header = struct.pack("<8sHHHIII", MAGIC, WIDTH, HEIGHT, 0, len(black), len(red), crc)
    bin_data = header + payload

    png_path = CACHE_DIR / "latest.png"
    bin_path = CACHE_DIR / "latest.bin"
    tmp_png = CACHE_DIR / "latest.png.tmp"
    tmp_bin = CACHE_DIR / "latest.bin.tmp"
    preview.save(tmp_png, format="PNG", optimize=True)
    tmp_bin.write_bytes(bin_data)
    tmp_png.replace(png_path)
    tmp_bin.replace(bin_path)
    return png_path, bin_path, crc, len(bin_data)


def ensure_rendered_frame(payload, refresh_interval_sec=300, force=False):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    max_age = max(30, int(refresh_interval_sec or 300))
    source_hash = _source_hash(payload)
    manifest = _load_manifest()
    if not force and _cache_valid(manifest, source_hash, max_age):
        return manifest
    with _RENDER_LOCK:
        manifest = _load_manifest()
        if not force and _cache_valid(manifest, source_hash, max_age):
            return manifest

        rendered_html = _write_render_html(payload)
        raw_png = _screenshot(rendered_html)
        png_path, bin_path, crc, byte_len = _quantize_and_pack(raw_png)
        generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        manifest = {
            "version": generated,
            "generated_at": generated,
            "generated_at_epoch": time.time(),
            "source_hash": source_hash,
            "width": WIDTH,
            "height": HEIGHT,
            "format": FORMAT,
            "url": "/render/eink.bin",
            "png_url": "/render/eink.png",
            "crc32": f"{crc:08x}",
            "bytes": byte_len,
            "refresh_interval": refresh_interval_sec,
            "cache": {
                "png": str(png_path),
                "bin": str(bin_path),
            },
        }
        tmp_manifest = CACHE_DIR / "latest.json.tmp"
        tmp_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_manifest.replace(CACHE_DIR / "latest.json")
        return manifest
