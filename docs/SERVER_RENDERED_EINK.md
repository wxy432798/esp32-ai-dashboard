# Server Rendered E-Ink Dashboard

This document describes the long-term dashboard architecture for the ESP32
4.2 inch tri-color e-paper device.

The firmware should stay small and stable. UI layout, fonts, icons, and module
composition should live on the Linux server.

## Goal

Render the dashboard as HTML/CSS on the server, convert it into a 400 x 300
tri-color e-paper frame, and let the ESP32 download and display that frame.

```text
HTML/CSS dashboard
  -> Linux server
  -> Playwright or Puppeteer
  -> Headless Chrome screenshot
  -> PNG preview
  -> black/white/red quantization
  -> packed e-paper frame BIN
  -> ESP32 HTTP download
  -> GDEY042Z98 display refresh
```

## Why This Architecture

- UI can change without flashing ESP32 firmware.
- Browser rendering gives better typography and layout control.
- Claude-generated HTML/CSS can be used as the design source.
- ESP32 only handles Wi-Fi, HTTP, frame validation, display output, button
  refresh, sleep, and OTA.
- Server-side rendering makes future modules easier to add.

## Recommended Repository Layout

```text
frontend/
  eink-dashboard.html
  styles.css
  assets/
  data.sample.json

renderer/
  render-frame.js
  quantize-frame.js
  pack-frame.js

server/
  backend.py
  providers/
  render_cache/

firmware/
  src/
  include/
```

## Server Responsibilities

The server should provide two kinds of APIs:

1. Data APIs for the HTML page.
2. Rendered frame APIs for the ESP32.

Recommended endpoints:

```text
GET /api/eink-dashboard
GET /render/eink.png
GET /render/eink.bin
GET /render/eink.bin?offset=0&length=4096
GET /render/manifest.json
```

`/api/eink-dashboard` returns dashboard data as JSON.

`/render/eink.png` returns a human-viewable 400 x 300 PNG preview.

`/render/eink.bin` returns the packed tri-color bitplanes for the ESP32.

`/render/eink.bin?offset=0&length=4096` returns a small byte range from the
same BIN frame. This is the preferred ESP32 download mode on weak Wi-Fi links,
because repeated short HTTP responses are more reliable than one 30KB response.

`/render/manifest.json` tells the ESP32 whether a new frame is available:

```json
{
  "version": "2026-07-10T00:40:00Z",
  "width": 400,
  "height": 300,
  "format": "eink3c-bin-v1",
  "url": "/render/eink.bin",
  "crc32": "abcd1234",
  "refresh_interval": 300
}
```

## Rendering Pipeline

Use Playwright or Puppeteer on the Linux server.

Recommended first implementation:

```text
1. Load frontend/eink-dashboard.html.
2. Inject dashboard JSON.
3. Set viewport to 400 x 300.
4. Wait for fonts and layout to settle.
5. Capture a PNG screenshot.
6. Quantize PNG pixels to white, black, or red.
7. Pack pixels into black and red 1-bit planes.
8. Save PNG preview and BIN frame to cache.
```

Use `sharp` for image processing if the renderer is Node.js.

## Frame Format

Use a custom raw binary format for ESP32. Avoid PNG decoding on ESP32.

For a 400 x 300 tri-color screen:

```text
pixels = 400 * 300 = 120000
black plane = 120000 / 8 = 15000 bytes
red plane = 120000 / 8 = 15000 bytes
payload ~= 30000 bytes
```

Recommended BIN format:

```text
magic:      8 bytes   "EINK3C01"
width:      uint16_le 400
height:     uint16_le 300
flags:      uint16_le reserved
black_len:  uint32_le 15000
red_len:    uint32_le 15000
crc32:      uint32_le payload CRC32
payload:
  black bitplane
  red bitplane
```

Bit convention should be documented in firmware. Suggested convention:

- black bit = 1 means black pixel.
- red bit = 1 means red pixel.
- if both are 0, pixel is white.
- if both are 1, red wins or the server must prevent this state.

## Quantization Rules

The browser screenshot is RGB/RGBA. Convert every pixel to one of:

- white
- black
- red/orange

Suggested first-pass rules:

```text
if red channel is dominant and saturation is high -> red
else if luminance < threshold -> black
else -> white
```

Keep the HTML design simple:

- white/off-white background
- black text and lines
- red/orange only for status, limits, warnings, and emphasis
- no gradients inside the final 400 x 300 dashboard area
- no tiny gray text

## Caching

Do not run Chrome for every ESP32 request.

Recommended cache behavior:

```text
render_cache/
  latest.json
  latest.png
  latest.bin
```

Render a new frame when:

- dashboard data changes,
- the HTML/CSS version changes,
- the refresh interval expires,
- a manual refresh is requested.

ESP32 should usually request `manifest.json` first. If `version` and `crc32`
are unchanged, it can skip downloading the BIN.

The first deployed implementation intentionally keeps only `latest.*` files.
It overwrites the previous frame instead of storing historical images, so a
5-minute refresh cadence does not grow disk usage over time.

## ESP32 Responsibilities

The ESP32 should not parse HTML or do UI layout.

Firmware flow:

```text
wake
connect Wi-Fi
GET /render/manifest.json
if unchanged: sleep
GET /render/eink.bin
validate magic, size, crc32
copy black/red bitplanes to display buffers
refresh e-paper
hibernate display
deep sleep or wait for next interval
```

Button behavior:

- short press: force refresh
- long press: cycle refresh interval or enter config mode

## Deployment Notes

On the server, install:

```bash
apt update
apt install -y nodejs npm chromium fonts-noto fonts-noto-cjk
npm install playwright sharp
npx playwright install --with-deps chromium
```

Docker is recommended for repeatable deployment. The container should include:

- Chromium runtime dependencies
- Playwright or Puppeteer
- CJK and Latin fonts
- backend app
- render cache volume

Recommended production setup:

```text
Nginx :80/:443
  -> backend container :8000
      /api/eink-dashboard
      /render/eink.png
      /render/eink.bin
      /render/manifest.json
```

Keep `X-API-Key` support for ESP32 endpoints before exposing this publicly.

## Expansion

OTA updates remain useful for firmware-level changes:

- Wi-Fi improvements
- frame format changes
- battery measurement
- deep sleep
- partial refresh
- button behavior
- recovery mode

Partial refresh can be added later with a manifest like:

```json
{
  "full": false,
  "rects": [{"x": 0, "y": 0, "w": 400, "h": 40}]
}
```

For the first stable version, prefer full refresh only.
