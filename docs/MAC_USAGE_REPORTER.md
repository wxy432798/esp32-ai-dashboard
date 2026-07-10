# Mac Usage Reporter

Personal Claude/Codex subscriptions do not expose a stable official usage API
for this dashboard. The Mac reporter solves that with two layers:

- Claude: by default, it tries the Clawdmeter-style probe. It reads the Claude
  Code OAuth token from `~/.claude/.credentials.json` or macOS Keychain service
  `Claude Code-credentials`, sends a 1-token Haiku request, and maps Anthropic
  rate-limit headers into the dashboard.
- Fallback/manual: it reads `~/.esp32-dashboard-usage.json` and sends that to
  the server's `POST /api/usage` endpoint.

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

To skip the Claude API probe and only send the local JSON file:

```bash
python3 tools/mac_usage_reporter.py --no-auto-claude
```

Claude fields map as:

```text
daily_percent  = anthropic-ratelimit-unified-5h-utilization
daily_reset    = anthropic-ratelimit-unified-5h-reset
weekly_percent = anthropic-ratelimit-unified-7d-utilization
weekly_reset   = anthropic-ratelimit-unified-7d-reset
status         = anthropic-ratelimit-unified-5h-status
```

The request is intentionally tiny:

```text
POST https://api.anthropic.com/v1/messages
model: claude-haiku-4-5-20251001
max_tokens: 1
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
