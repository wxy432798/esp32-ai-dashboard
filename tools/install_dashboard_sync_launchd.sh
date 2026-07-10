#!/usr/bin/env bash
set -euo pipefail

INTERVAL_SECONDS="${1:-60}"
SOURCE="${2:-http://107.172.147.113:8787}"
PREFIX="${3:-render}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_DIR}/tools/sync_dashboard_frame.py"
ENV_FILE="${HOME}/.esp32-dashboard-oss.env"
KEY_FILE="${HOME}/.esp32-dashboard-admin-key"
PLIST="${HOME}/Library/LaunchAgents/com.esp32-dashboard.sync-frame.plist"
LOG_DIR="${HOME}/Library/Logs/esp32-dashboard"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"

if [[ -z "${PYTHON_BIN}" || ! -x "${PYTHON_BIN}" ]]; then
  echo "missing python3; set PYTHON_BIN=/path/to/python3" >&2
  exit 2
fi

if [[ ! -s "${KEY_FILE}" && -z "${ADMIN_API_KEY:-}" ]]; then
  echo "missing admin key; create ${KEY_FILE} or export ADMIN_API_KEY" >&2
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
  <string>com.esp32-dashboard.sync-frame</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_BIN}</string>
    <string>${SCRIPT}</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHON_BIN</key>
    <string>${PYTHON_BIN}</string>
    <key>SOURCE</key>
    <string>${SOURCE}</string>
    <key>PREFIX</key>
    <string>${PREFIX}</string>
    <key>ENV_FILE</key>
    <string>${ENV_FILE}</string>
  </dict>
  <key>StartInterval</key>
  <integer>${INTERVAL_SECONDS}</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/sync-frame.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/sync-frame.err.log</string>
</dict>
</plist>
EOF

chmod +x "${SCRIPT}"
launchctl unload "${PLIST}" >/dev/null 2>&1 || true
launchctl load "${PLIST}"

echo "installed: ${PLIST}"
echo "interval: ${INTERVAL_SECONDS}s"
echo "source: ${SOURCE}"
echo "prefix: ${PREFIX}"
echo "python: ${PYTHON_BIN}"
echo "logs: ${LOG_DIR}/sync-frame.out.log"
