# ESP32 AI Dashboard

4.2 inch tri-color e-paper dashboard for AI usage, server status, weather,
to-do and notes.

## Scope

The ESP32 only does four things:

- connect to Wi-Fi
- fetch a server-rendered e-paper frame from the server
- validate and display black/red bitplanes
- refresh on timer or side button

All business logic, UI layout, fonts and image quantization stay server-side.
The firmware does not parse HTML and no longer draws the dashboard UI itself.

Refresh behavior:

- default auto refresh: 5 minutes
- server may override cadence with `refresh_interval`
- short press side button: refresh immediately
- long press side button: cycle local cadence through 1 / 5 / 10 / 15 / 30 / 60 minutes
- unchanged frame CRC: skip download
- failed request: show a small fallback error screen

## Project Layout

```text
esp32-ai-dashboard/
  data/mock/dashboard.json        Mock API response
  docs/ARCHITECTURE.md            System architecture
  docs/API.md                     Dashboard JSON contract
  docs/BACKEND.md                 Backend implementation notes
  docs/SERVER_RENDERED_EINK.md    HTML/CSS -> PNG -> BIN frame pipeline
  frontend/eink-dashboard.html    400 x 300 server-rendered dashboard template
  firmware/                       PlatformIO firmware project
  server/mock_server.py           Local mock HTTP server
  server/backend.py               Real backend skeleton
```

## Local Mock Server

```bash
cd /root/esp32-ai-dashboard
python3 server/mock_server.py --host 0.0.0.0 --port 8787
```

Endpoint:

```text
GET /api/eink-dashboard
GET /render/manifest.json
GET /render/eink.png
GET /render/eink.bin
```

## Backend Server

```bash
cd /root/esp32-ai-dashboard
python3 server/backend.py --host 0.0.0.0 --port 8787 --refresh 300
```

The backend already returns real Linux server metrics and mock/provider-based
Claude, Codex and weather data. See `docs/BACKEND.md`.

## Personal Subscription Usage

Personal Claude/ChatGPT/Codex subscriptions do not provide a stable admin
usage API for this kind of dashboard. For personal accounts, report the values
you want to display into the server:

```bash
curl -X POST "http://127.0.0.1:8787/api/usage" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -d '{
    "claude": {
      "daily_percent": 0,
      "weekly_percent": 0,
      "daily_reset": "N/A",
      "weekly_reset": "N/A",
      "model": "Claude",
      "requests_today": 0,
      "used_today": "personal"
    },
    "codex": {
      "daily_percent": 0,
      "weekly_percent": 0,
      "daily_reset": "N/A",
      "weekly_reset": "N/A",
      "model": "Codex",
      "requests_today": 0,
      "used_today": "personal"
    }
  }'
```

The backend stores these values in `data/state/usage/claude.json` and
`data/state/usage/codex.json`. If no reported value exists, it falls back to
`data/mock/dashboard.json`.

## Firmware

1. Copy config:

```bash
cp firmware/include/config.example.h firmware/include/config.h
```

2. Edit Wi-Fi, API URL and display pins in `firmware/include/config.h`.

For the current server-rendered frame mode, configure:

```c
#define DASHBOARD_API_HOST "107.172.147.113"
#define DASHBOARD_API_PORT 80
#define DASHBOARD_MANIFEST_PATH "/render/manifest.json"
#define DASHBOARD_FRAME_PATH "/render/eink.bin"
```

3. Build/upload with PlatformIO:

```bash
cd firmware
pio run
pio run -t upload
```

The exact e-paper panel driver may need one line adjusted in
`firmware/include/DisplayConfig.h`, because 4.2 inch tri-color panels ship with
different controllers.
