# Architecture

## Design Rule

The firmware renders a server-provided view model. It does not calculate Claude
usage, Codex usage, server load, weather, to-do priority, note selection or
quota logic.

## Components

```text
                ┌─────────────────────────────────────────┐
                │ Server                                  │
                │                                         │
                │ Claude usage / Codex usage              │
                │ Server status / Weather / To-do / Notes │
                │                                         │
                │ Produces one JSON view model            │
                └───────────────────┬─────────────────────┘
                                    │ HTTP GET /api/eink-dashboard
                                    ▼
┌────────────────────────────────────────────────────────────────┐
│ ESP32-WROOM-32UE                                                │
│                                                                 │
│  WiFiClient  →  DashboardApi  →  DashboardData  →  DashboardUI  │
│                                                                 │
│  Side button: short press refresh / long press cadence cycle     │
│  Timer: auto refresh                                             │
│  E-paper: full redraw                                            │
└────────────────────────────────────────────────────────────────┘
```

## Firmware Boundaries

`DashboardApi`
: Fetches JSON from `/api/eink-dashboard`.

`DashboardData`
: Plain display structs. The parser maps the server API into UI-ready structs,
  but does not calculate business logic.

`DashboardUI`
: Draws the current data into a fixed 400 x 300 landscape layout.

`main.cpp`
: Owns Wi-Fi, refresh timer, side button and sleep/loop behavior.

## UI Assumptions

- Landscape 4.2 inch e-paper, usually 400 x 300 px.
- Three colors: white background, black text/lines, red accent.
- The mock keeps semantic accents such as `blue`, but real tri-color e-paper
  maps unsupported colors to black.
- No touch.
- Side button can force refresh.
- Long-press side button cycles local refresh cadence.
- Full refresh is preferred for tri-color stability.
- Chinese text needs a font strategy; see `FONTING.md`.

## Refresh Strategy

Current behavior:

- auto refresh every 5 minutes by default
- server `refresh_interval_sec` can override local refresh cadence
- short press side button: request server immediately and redraw
- long press side button: cycle local refresh cadence and persist it on-device
- failed fetch: keep the last successful dashboard data and render
  `Last Sync Failed`

Local refresh cadence cycle:

```text
1 min -> 5 min -> 10 min -> 15 min -> 30 min -> 60 min -> 1 min
```

If the server returns `refresh_interval_sec`, that value is used for scheduling.
The local setting is still saved and becomes the fallback when the server omits
the field.

Future improvement:

- deep sleep between refreshes
- ETag / hash endpoint to avoid unnecessary e-paper refreshes
- server-side layout variants

## To-Do Editing

To-do changes are server-side only. The e-paper device never edits tasks.

Examples handled by the Telegram/server layer:

```text
/todo add 投稿 法国灯光节
/todo done 2
/todo del 3
```

## No Quick Actions

The device is not touch-capable and the UI should not render buttons or quick
actions. Every mutation happens through the server/Telegram command layer.
