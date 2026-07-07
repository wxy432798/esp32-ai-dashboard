import os
import shutil
from pathlib import Path


def _read_meminfo() -> dict:
    values = {}
    for line in Path("/proc/meminfo").read_text(errors="ignore").splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        parts = raw.strip().split()
        if parts and parts[0].isdigit():
            values[key] = int(parts[0]) * 1024
    return values


def _cpu_percent() -> int:
    try:
        load1 = os.getloadavg()[0]
        cores = os.cpu_count() or 1
        return max(0, min(100, round((load1 / cores) * 100)))
    except OSError:
        return 0


def _ram_percent() -> int:
    mem = _read_meminfo()
    total = mem.get("MemTotal", 0)
    available = mem.get("MemAvailable", 0)
    if not total:
        return 0
    return max(0, min(100, round(((total - available) / total) * 100)))


def _disk_percent(path="/") -> int:
    usage = shutil.disk_usage(path)
    if not usage.total:
        return 0
    return max(0, min(100, round((usage.used / usage.total) * 100)))


def _uptime() -> str:
    try:
        seconds = float(Path("/proc/uptime").read_text().split()[0])
    except Exception:
        return "unknown"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    return f"{days}d{hours}h" if days else f"{hours}h"


def get_server_status() -> dict:
    load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
    return {
        "online": True,
        "cpu": _cpu_percent(),
        "ram": _ram_percent(),
        "disk": _disk_percent("/"),
        "load_avg": round(load, 2),
        "uptime": _uptime(),
    }

