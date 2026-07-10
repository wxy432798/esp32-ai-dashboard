# Mac Usage Reporter

Personal Claude/Codex subscriptions do not expose a stable official usage API
for this dashboard. The Mac reporter solves that by sending a small local JSON
state file to the server's `POST /api/usage` endpoint.

## One-Time Setup

Copy the server admin key to the Mac:

```bash
ssh root@107.172.147.113 'cat /root/.esp32-dashboard-admin-key' > ~/.esp32-dashboard-admin-key
chmod 600 ~/.esp32-dashboard-admin-key
```

Create the local usage file:

```bash
cd /Users/xyw/Documents/Codex/2026-07-07/cloud-esp32-wroom-32ue-n8/work/ai-usage-dashboard
python3 tools/mac_usage_reporter.py --init
```

Edit:

```text
~/.esp32-dashboard-usage.json
```

Example:

```json
{
  "claude": {
    "daily_percent": 0,
    "weekly_percent": 0,
    "daily_reset": "N/A",
    "weekly_reset": "N/A",
    "model": "Claude",
    "requests_today": 0,
    "used_today": "personal",
    "status": "Active"
  },
  "codex": {
    "daily_percent": 0,
    "weekly_percent": 0,
    "daily_reset": "N/A",
    "weekly_reset": "N/A",
    "model": "Codex",
    "requests_today": 0,
    "used_today": "personal",
    "status": "Running"
  }
}
```

## Test Once

```bash
python3 tools/mac_usage_reporter.py --dry-run
python3 tools/mac_usage_reporter.py
```

The second command should return:

```json
{"ok": true}
```

## Install 5-Minute Timer

```bash
chmod +x tools/mac_usage_reporter.py tools/install_mac_usage_reporter_launchd.sh
tools/install_mac_usage_reporter_launchd.sh 300
```

Logs:

```text
~/Library/Logs/esp32-dashboard/usage-reporter.out.log
~/Library/Logs/esp32-dashboard/usage-reporter.err.log
```

Disable:

```bash
launchctl unload ~/Library/LaunchAgents/com.esp32-dashboard.usage-reporter.plist
```

## Data Flow

```text
~/.esp32-dashboard-usage.json
  -> tools/mac_usage_reporter.py
  -> http://107.172.147.113:8787/api/usage
  -> server data/state/usage/*.json
  -> /render/eink.bin
  -> ESP32 e-paper screen
```
