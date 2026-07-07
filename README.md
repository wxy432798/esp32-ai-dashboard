# ESP32 AI Dashboard

4.2 inch tri-color e-paper dashboard for AI usage, server status, weather,
to-do and notes.

## Scope

The ESP32 only does four things:

- connect to Wi-Fi
- fetch one dashboard JSON document from the server
- render the UI
- refresh on timer or side button

All business logic stays server-side. The firmware treats the API response as a
view model, not as raw business data.

Refresh behavior:

- default auto refresh: 5 minutes
- server may override cadence with `refresh_interval_sec`
- short press side button: refresh immediately
- long press side button: cycle local cadence through 1 / 5 / 10 / 15 / 30 / 60 minutes
- failed request: keep cached content and show `Last Sync Failed`

## Project Layout

```text
esp32-ai-dashboard/
  data/mock/dashboard.json        Mock API response
  docs/ARCHITECTURE.md            System architecture
  docs/API.md                     Dashboard JSON contract
  firmware/                       PlatformIO firmware project
  server/mock_server.py           Local mock HTTP server
```

## Local Mock Server

```bash
cd /root/esp32-ai-dashboard
python3 server/mock_server.py --host 0.0.0.0 --port 8787
```

Endpoint:

```text
GET /api/eink-dashboard
```

## Firmware

1. Copy config:

```bash
cp firmware/include/config.example.h firmware/include/config.h
```

2. Edit Wi-Fi, API URL and display pins in `firmware/include/config.h`.

3. Build/upload with PlatformIO:

```bash
cd firmware
pio run
pio run -t upload
```

The exact e-paper panel driver may need one line adjusted in
`firmware/include/DisplayConfig.h`, because 4.2 inch tri-color panels ship with
different controllers.
