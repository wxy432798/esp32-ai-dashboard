#include <Arduino.h>
#include <Preferences.h>
#include <SPI.h>
#include <WiFi.h>

#include "DashboardApi.h"
#include "DashboardUI.h"
#include "DisplayConfig.h"
#include "config.h"

DashboardDisplay display(GxEPD2_420c(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));
DashboardUI ui(display);
DashboardApi api;
DashboardData dashboard;
Preferences prefs;

uint32_t nextRefreshAt = 0;
String lastStatus = "booting";
uint16_t localRefreshSeconds = DEFAULT_REFRESH_SECONDS;

static const uint16_t REFRESH_OPTIONS[] = {60, 300, 600, 900, 1800, 3600};
static const size_t REFRESH_OPTIONS_COUNT = sizeof(REFRESH_OPTIONS) / sizeof(REFRESH_OPTIONS[0]);
static const uint32_t LONG_PRESS_MS = 1200;

static uint16_t effectiveRefreshSeconds() {
  if (dashboard.meta.hasServerRefreshInterval && dashboard.meta.refreshSeconds > 0) {
    return dashboard.meta.refreshSeconds;
  }
  return localRefreshSeconds;
}

static void loadRefreshPreference() {
  prefs.begin("dashboard", false);
  localRefreshSeconds = prefs.getUShort("refresh_s", DEFAULT_REFRESH_SECONDS);
}

static void saveRefreshPreference(uint16_t seconds) {
  localRefreshSeconds = seconds;
  prefs.putUShort("refresh_s", seconds);
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
  lastStatus = "Refresh " + String(localRefreshSeconds / 60) + " min saved";
  ui.render(dashboard, lastStatus);
}

static void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("WiFi");
  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 20000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    lastStatus = "online";
  } else {
    lastStatus = "wifi failed";
  }
}

static void refreshDashboard(bool forced) {
  if (WiFi.status() != WL_CONNECTED) connectWifi();

  String error;
  if (WiFi.status() == WL_CONNECTED && api.fetch(dashboard, error)) {
    lastStatus = forced ? "manual refresh ok" : "refresh ok";
  } else {
    lastStatus = "Last Sync Failed";
  }

  ui.render(dashboard, lastStatus);
  nextRefreshAt = millis() + effectiveRefreshSeconds() * 1000UL;
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(PIN_SIDE_BUTTON, INPUT_PULLUP);
  SPI.begin(EPD_SCK, -1, EPD_MOSI, EPD_CS);
  loadRefreshPreference();

  ui.begin();
  connectWifi();
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
      refreshDashboard(true);
    }
  }
  lastButton = button;

  if ((int32_t)(millis() - nextRefreshAt) >= 0) {
    refreshDashboard(false);
  }

  delay(50);
}
