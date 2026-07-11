#pragma once

// Copy this file to config.h and edit values.

#define WIFI_SSID "YOUR_WIFI"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Optional: add multiple known networks so the device can roam without
// reflashing firmware whenever you switch hotspot/router.
// #define WIFI_NETWORKS { \
//   {"YOUR_HOME_WIFI", "YOUR_HOME_PASSWORD"}, \
//   {"YOUR_PHONE_HOTSPOT", "YOUR_PHONE_PASSWORD"}, \
// }

// The raw HTTP client uses host/port/path so it can retry reliably on ESP32.
#define DASHBOARD_API_HOST "YOUR_SERVER"
#define DASHBOARD_API_PORT 80
#define DASHBOARD_MANIFEST_PATH "/render/manifest.json"
#define DASHBOARD_FRAME_PATH "/render/eink.bin"

// OSS direct-read example. Keep OSS AccessKey only on Mac/server upload side.
// #define DASHBOARD_API_HOST "claudecodesapi.oss-cn-chengdu.aliyuncs.com"
// #define DASHBOARD_API_PORT 80
// #define DASHBOARD_MANIFEST_PATH "/render/manifest.json"
// #define DASHBOARD_FRAME_PATH "/render/eink.bin"

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
