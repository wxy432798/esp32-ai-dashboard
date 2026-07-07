#pragma once

// Copy this file to config.h and edit values.

#define WIFI_SSID "YOUR_WIFI"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Example: "http://192.168.1.10:8787/api/eink-dashboard"
#define DASHBOARD_API_URL "http://192.168.1.10:8787/api/eink-dashboard"

// Refresh fallback if the server does not provide meta.refresh_seconds.
#define DEFAULT_REFRESH_SECONDS 300

// Side button: active LOW, using INPUT_PULLUP.
#define PIN_SIDE_BUTTON 0

// Typical ESP32 + e-paper SPI wiring. Adjust to your board.
#define EPD_BUSY 4
#define EPD_RST 16
#define EPD_DC 17
#define EPD_CS 5
#define EPD_SCK 18
#define EPD_MOSI 23
