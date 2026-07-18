#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8788}"
UPSTREAM="${2:-http://107.172.147.113:8787}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_DIR}/tools/local_eink_relay.py"
PLIST="${HOME}/Library/LaunchAgents/com.esp32-dashboard.local-eink-relay.plist"
LOG_DIR="${HOME}/Library/Logs/esp32-dashboard"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"

if [[ -z "${PYTHON_BIN}" || ! -x "${PYTHON_BIN}" ]]; then
  echo "missing python3; set PYTHON_BIN=/path/to/python3" >&2
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
  <string>com.esp32-dashboard.local-eink-relay</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_BIN}</string>
    <string>${SCRIPT}</string>
    <string>--host</string>
    <string>0.0.0.0</string>
    <string>--port</string>
    <string>${PORT}</string>
    <string>--upstream</string>
    <string>${UPSTREAM}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/local-eink-relay.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/local-eink-relay.err.log</string>
</dict>
</plist>
EOF

launchctl unload "${PLIST}" >/dev/null 2>&1 || true
launchctl load "${PLIST}"

echo "installed: ${PLIST}"
echo "relay: 0.0.0.0:${PORT} -> ${UPSTREAM}"
echo "python: ${PYTHON_BIN}"
echo "logs: ${LOG_DIR}/local-eink-relay.out.log"
