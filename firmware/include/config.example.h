#pragma once

// Copy this file to config.h and edit values.

#define WIFI_SSID "YOUR_WIFI"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Example final URL: "http://107.172.147.113/api/eink-dashboard".
// The raw HTTP client uses host/port/path so it can retry reliably on ESP32.
#define DASHBOARD_API_URL "http://YOUR_SERVER/api/eink-dashboard"
#define DASHBOARD_API_HOST "YOUR_SERVER"
#define DASHBOARD_API_PORT 80
#define DASHBOARD_API_PATH "/api/eink-dashboard"

// Optional. Leave empty if the backend endpoint is in open test mode.
#define ESP32_API_KEY ""

// Refresh fallback if the server does not provide meta.refresh_seconds.
#define DEFAULT_REFRESH_SECONDS 300

// Side button: active LOW, using INPUT_PULLUP.
#define PIN_SIDE_BUTTON 0

// Confirmed ESP32 + GDEY042Z98 e-paper SPI wiring.
#define EPD_BUSY 4
#define EPD_RST 16
#define EPD_DC 17
#define EPD_CS 5
#define EPD_SCK 18
#define EPD_MOSI 23
