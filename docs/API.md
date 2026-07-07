# E-Ink Dashboard API Contract

Endpoint:

```text
GET /api/eink-dashboard
```

The ESP32 treats this response as the only source of truth. It displays the
data and never modifies to-do items or computes business logic.

## Response

```json
{
  "refresh_interval_sec": 300,
  "updated_at": "2026-07-07 02:36",
  "claude": {
    "daily_percent": 72,
    "weekly_percent": 68,
    "daily_reset": "1h24m",
    "weekly_reset": "5d3h",
    "model": "Opus",
    "requests_today": 128,
    "used_today": "3h12m"
  },
  "codex": {
    "daily_percent": 58,
    "weekly_percent": 43,
    "daily_reset": "3h12m",
    "weekly_reset": "4d8h",
    "model": "GPT-4o",
    "requests_today": 96,
    "used_today": "1h48m"
  },
  "server": {
    "online": true,
    "cpu": 18,
    "ram": 46,
    "disk": 32,
    "load_avg": 0.28,
    "uptime": "5d12h"
  },
  "weather": {
    "temperature": 28.6,
    "humidity": 62,
    "wind": "SE",
    "wind_speed": "2.1m/s",
    "condition": "Cloudy"
  },
  "todos": [
    { "text": "投稿 法国灯光节", "due": "07-10", "done": false }
  ],
  "note": "保持专注，持续创造。"
}
```

## Field Rules

- `refresh_interval_sec`: device refresh cadence.
  If omitted, the ESP32 uses its local saved refresh cadence.
- `updated_at`: display string; firmware only extracts date/time for header.
- `claude` / `codex`: usage cards.
- `server.online`: maps to `ONLINE` / `OFFLINE`.
- `todos`: display-only. Recommended item shape is
  `{ "text": "...", "due": "MM-DD", "done": true|false }`.
- `note`: single display note.

## To-Do Commands

To-do mutations happen on the server side, not on the ESP32:

```text
/todo add 投稿 法国灯光节
/todo done 2
/todo del 3
```

There are no device-side buttons or quick actions for task mutation.

## Mock Data

See `data/mock/dashboard.json`.
