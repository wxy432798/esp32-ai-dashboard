# Backend

The backend exposes the device API and owns all business logic.

## Endpoint

```text
GET /api/eink-dashboard
```

The response matches `docs/API.md`.

## Responsibilities

- collect Claude usage
- collect Codex usage
- collect server metrics
- collect weather
- read to-do list
- read notes
- assemble one display JSON document

The ESP32 never edits server state.

## Current Implementation

`server/backend.py` is a dependency-free Python HTTP server.

It already reads real server metrics from Linux:

- CPU approximation from load average / CPU cores
- RAM from `/proc/meminfo`
- disk from `shutil.disk_usage("/")`
- load average from `os.getloadavg()`
- uptime from `/proc/uptime`

Claude/Codex usage is provider-based:

- default: `data/mock/dashboard.json`
- override with files:

```bash
CLAUDE_USAGE_JSON=/path/claude.json
CODEX_USAGE_JSON=/path/codex.json
```

Weather is also provider-based:

```bash
WEATHER_JSON=/path/weather.json
```

## Run

```bash
cd /root/esp32-ai-dashboard
python3 server/backend.py --host 0.0.0.0 --port 8787 --refresh 300
```

Then configure ESP32:

```c
#define DASHBOARD_API_URL "http://SERVER_IP:8787/api/eink-dashboard"
```

## To-Do / Note Mutation API

These are for the server/Telegram layer, not the device.

```bash
curl -X POST http://127.0.0.1:8787/api/todo \
  -H 'content-type: application/json' \
  -d '{"action":"add","text":"投稿 法国灯光节","due":"07-10"}'

curl -X POST http://127.0.0.1:8787/api/todo \
  -H 'content-type: application/json' \
  -d '{"action":"done","index":2}'

curl -X POST http://127.0.0.1:8787/api/todo \
  -H 'content-type: application/json' \
  -d '{"action":"del","index":3}'

curl -X POST http://127.0.0.1:8787/api/note \
  -H 'content-type: application/json' \
  -d '{"note":"保持专注，持续创造。"}'
```

## Next Real API Work

Replace `server/providers/ai_usage.py` with real sources.

Possible sources:

- local Claude/Codex usage files if the CLI exposes them
- a paid API usage endpoint if available
- server-side accounting that records each agent request as it happens

The dashboard endpoint should not change when those providers become real.

