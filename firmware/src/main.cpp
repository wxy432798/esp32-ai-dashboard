#include <Arduino.h>
#include <Preferences.h>
#include <SPI.h>
#include <WiFi.h>
#include <esp_wifi.h>

#include "DashboardApi.h"
#include "DashboardUI.h"
#include "DisplayConfig.h"
#include "config.h"

DashboardDisplay display(DashboardPanel(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));
DashboardUI ui(display);
DashboardApi api;
FrameManifest manifest;
EInkFrame frame;
Preferences prefs;

uint32_t nextRefreshAt = 0;
uint16_t localRefreshSeconds = DEFAULT_REFRESH_SECONDS;
String lastFrameCrc;

static const uint16_t REFRESH_OPTIONS[] = {60, 300, 600, 900, 1800, 3600};
static const size_t REFRESH_OPTIONS_COUNT = sizeof(REFRESH_OPTIONS) / sizeof(REFRESH_OPTIONS[0]);
static const uint32_t LONG_PRESS_MS = 1200;

static uint16_t effectiveRefreshSeconds() {
  if (manifest.refreshSeconds > 0) return manifest.refreshSeconds;
  return localRefreshSeconds;
}

static void loadPreferences() {
  prefs.begin("dashboard", false);
  localRefreshSeconds = prefs.getUShort("refresh_s", DEFAULT_REFRESH_SECONDS);
  lastFrameCrc = prefs.getString("frame_crc", "");
}

static void saveRefreshPreference(uint16_t seconds) {
  localRefreshSeconds = seconds;
  prefs.putUShort("refresh_s", seconds);
}

static void saveFrameCrc(const String& crc) {
  lastFrameCrc = crc;
  prefs.putString("frame_crc", crc);
}

static void cycleRefreshPreference() {
  size_t next = 0;
  for (size_t i = 0; i < REFRESH_OPTIONS_COUNT; i++) {
    if (REFRESH_OPTIONS[i] == localRefreshSeconds) {
      next = (i + 1) % REFRESH_OPTIONS_COUNT;
      break;
    }
  }
  saveRefreshPreference(REFRESH_OPTIONS[next]);
  Serial.printf("Local refresh interval saved: %u seconds\n", localRefreshSeconds);
}

static void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  esp_wifi_set_ps(WIFI_PS_NONE);
  Serial.printf("WiFi SSID=%s", WIFI_SSID);

  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 20000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("IP=%s RSSI=%d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  } else {
    Serial.println("WiFi failed");
  }
}

static void refreshDashboard(bool forced) {
  connectWifi();

  String error;
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi failed; preserving current e-paper image");
    nextRefreshAt = millis() + static_cast<uint32_t>(localRefreshSeconds) * 1000UL;
    return;
  }

  if (!api.fetchManifest(manifest, error)) {
    Serial.printf("Manifest failed: %s\n", error.c_str());
    Serial.println("Manifest failed; preserving current e-paper image");
    nextRefreshAt = millis() + static_cast<uint32_t>(localRefreshSeconds) * 1000UL;
    return;
  }

  if (!forced && manifest.crc32Hex == lastFrameCrc) {
    Serial.printf("Frame unchanged crc=%s; skipping download\n", manifest.crc32Hex.c_str());
    nextRefreshAt = millis() + static_cast<uint32_t>(effectiveRefreshSeconds()) * 1000UL;
    return;
  }

  if (!api.fetchFrame(manifest, frame, error)) {
    Serial.printf("Frame failed: %s\n", error.c_str());
    Serial.println("Frame failed; preserving current e-paper image");
    nextRefreshAt = millis() + static_cast<uint32_t>(effectiveRefreshSeconds()) * 1000UL;
    return;
  }

  ui.renderFrame(frame);
  saveFrameCrc(manifest.crc32Hex);
  Serial.printf("Displayed frame crc=%s refresh=%us forced=%s\n",
                manifest.crc32Hex.c_str(), effectiveRefreshSeconds(),
                forced ? "true" : "false");
  nextRefreshAt = millis() + static_cast<uint32_t>(effectiveRefreshSeconds()) * 1000UL;
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println("ESP32 server-rendered e-ink dashboard boot");

  pinMode(PIN_SIDE_BUTTON, INPUT_PULLUP);
  SPI.begin(EPD_SCK, -1, EPD_MOSI, EPD_CS);
  loadPreferences();

  ui.begin();
  refreshDashboard(true);
}

void loop() {
  static bool lastButton = HIGH;
  static uint32_t pressedAt = 0;
  static bool longHandled = false;
  bool button = digitalRead(PIN_SIDE_BUTTON);

  if (lastButton == HIGH && button == LOW) {
    pressedAt = millis();
    longHandled = false;
  }

  if (button == LOW && !longHandled && millis() - pressedAt >= LONG_PRESS_MS) {
    longHandled = true;
    cycleRefreshPreference();
  }

  if (lastButton == LOW && button == HIGH) {
    uint32_t held = millis() - pressedAt;
    if (!longHandled && held > 40) {
      Serial.println("Manual refresh");
      refreshDashboard(true);
    }
  }
  lastButton = button;

  if ((int32_t)(millis() - nextRefreshAt) >= 0) {
    refreshDashboard(false);
  }

  delay(50);
}
