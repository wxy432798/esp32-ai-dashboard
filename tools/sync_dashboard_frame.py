#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_dir = Path(__file__).resolve().parents[1]
    python_bin = os.environ.get("PYTHON_BIN", sys.executable)
    source = os.environ.get("SOURCE", "http://107.172.147.113:8787")
    prefix = os.environ.get("PREFIX", "render")
    env_file = os.environ.get("ENV_FILE", str(Path.home() / ".esp32-dashboard-oss.env"))

    subprocess.run([python_bin, str(repo_dir / "tools" / "mac_usage_reporter.py")], check=True)
    subprocess.run([
        python_bin,
        str(repo_dir / "tools" / "publish_eink_to_oss.py"),
        "--env-file",
        env_file,
        "--source",
        source,
        "--prefix",
        prefix,
    ], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
