#!/usr/bin/env bash
set -euo pipefail

INTERVAL_SECONDS="${1:-300}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_DIR}/tools/mac_usage_reporter.py"
PLIST="${HOME}/Library/LaunchAgents/com.esp32-dashboard.usage-reporter.plist"
LOG_DIR="${HOME}/Library/Logs/esp32-dashboard"
SOURCE="${HOME}/.esp32-dashboard-usage.json"
KEY_FILE="${HOME}/.esp32-dashboard-admin-key"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"

if [[ -z "${PYTHON_BIN}" || ! -x "${PYTHON_BIN}" ]]; then
  echo "missing python3; set PYTHON_BIN=/path/to/python3" >&2
  exit 2
fi

if [[ ! -s "${SOURCE}" ]]; then
  echo "missing ${SOURCE}; run: python3 ${SCRIPT} --init" >&2
  exit 2
fi

if [[ -z "${ADMIN_API_KEY:-}" && ! -s "${KEY_FILE}" ]]; then
  echo "missing admin key; create ${KEY_FILE} or export ADMIN_API_KEY" >&2
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
  <string>com.esp32-dashboard.usage-reporter</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_BIN}</string>
    <string>${SCRIPT}</string>
  </array>
  <key>StartInterval</key>
  <integer>${INTERVAL_SECONDS}</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/usage-reporter.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/usage-reporter.err.log</string>
</dict>
</plist>
EOF

launchctl unload "${PLIST}" >/dev/null 2>&1 || true
launchctl load "${PLIST}"

echo "installed: ${PLIST}"
echo "interval: ${INTERVAL_SECONDS}s"
echo "python: ${PYTHON_BIN}"
echo "logs: ${LOG_DIR}/usage-reporter.out.log"
