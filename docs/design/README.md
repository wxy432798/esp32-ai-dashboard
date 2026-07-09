# ESP32 Dashboard Design Exports

This folder stores Claude-generated design source files for the 4.2 inch
tri-color ESP32 e-paper dashboard.

Current package:

- `ESP32界面设计规划.zip`

The ZIP contains exported HTML/CSS mockups, screenshots, support JS, and image
uploads. These files are design references for the server-rendered e-paper
pipeline described in `../SERVER_RENDERED_EINK.md`.

The ESP32 firmware should not parse these HTML files directly. The Linux server
should render the HTML with Playwright or Puppeteer, quantize the screenshot to
black/white/red, then publish a compact BIN frame for ESP32 download.

