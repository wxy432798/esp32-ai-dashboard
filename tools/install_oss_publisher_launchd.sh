#!/usr/bin/env bash
set -euo pipefail

INTERVAL_SECONDS="${1:-300}"
SOURCE="${2:-http://127.0.0.1:8788}"
PREFIX="${3:-render}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_DIR}/tools/publish_eink_to_oss.py"
ENV_FILE="${HOME}/.esp32-dashboard-oss.env"
PLIST="${HOME}/Library/LaunchAgents/com.esp32-dashboard.oss-publisher.plist"
LOG_DIR="${HOME}/Library/Logs/esp32-dashboard"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"

if [[ -z "${PYTHON_BIN}" || ! -x "${PYTHON_BIN}" ]]; then
  echo "missing python3; set PYTHON_BIN=/path/to/python3" >&2
  exit 2
fi

if [[ ! -s "${ENV_FILE}" ]]; then
  echo "missing ${ENV_FILE}; add OSS_ACCESS_KEY_ID and OSS_ACCESS_KEY_SECRET" >&2
  exit 2
fi

mkdir -p "${HOME}/Library/LaunchAgents" "${LOG_DIR}"

cat > "${PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.esp32-dashboard.oss-publisher</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_BIN}</string>
    <string>${SCRIPT}</string>
    <string>--env-file</string>
    <string>${ENV_FILE}</string>
    <string>--source</string>
    <string>${SOURCE}</string>
    <string>--prefix</string>
    <string>${PREFIX}</string>
  </array>
  <key>StartInterval</key>
  <integer>${INTERVAL_SECONDS}</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/oss-publisher.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/oss-publisher.err.log</string>
</dict>
</plist>
EOF

launchctl unload "${PLIST}" >/dev/null 2>&1 || true
launchctl load "${PLIST}"

echo "installed: ${PLIST}"
echo "interval: ${INTERVAL_SECONDS}s"
echo "source: ${SOURCE}"
echo "prefix: ${PREFIX}"
echo "python: ${PYTHON_BIN}"
echo "logs: ${LOG_DIR}/oss-publisher.out.log"
