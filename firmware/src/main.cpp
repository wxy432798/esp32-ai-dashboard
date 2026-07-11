#include <Arduino.h>
#include <Preferences.h>
#include <SPI.h>
#include <WiFi.h>
#include <esp_wifi.h>

#include "DashboardApi.h"
#include "DashboardUI.h"
#include "DisplayConfig.h"
#include "config.h"

struct WifiCredential {
  const char* ssid;
  const char* password;
};

#ifndef WIFI_NETWORKS
#define WIFI_NETWORKS {{WIFI_SSID, WIFI_PASSWORD}}
#endif

static const WifiCredential WIFI_CREDENTIALS[] = WIFI_NETWORKS;
static const size_t WIFI_CREDENTIALS_COUNT =
    sizeof(WIFI_CREDENTIALS) / sizeof(WIFI_CREDENTIALS[0]);

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

static bool validWifiCredential(size_t index) {
  return index < WIFI_CREDENTIALS_COUNT &&
         WIFI_CREDENTIALS[index].ssid != nullptr &&
         WIFI_CREDENTIALS[index].ssid[0] != '\0';
}

static bool waitForWifi(uint32_t timeoutMs) {
  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < timeoutMs) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  return WiFi.status() == WL_CONNECTED;
}

static bool connectWifiCredential(size_t index) {
  if (!validWifiCredential(index)) return false;

  WiFi.disconnect(false, false);
  delay(100);
  WiFi.begin(WIFI_CREDENTIALS[index].ssid, WIFI_CREDENTIALS[index].password);
  Serial.printf("WiFi SSID=%s", WIFI_CREDENTIALS[index].ssid);

  if (!waitForWifi(16000)) return false;

  prefs.putInt("wifi_i", static_cast<int>(index));
  Serial.printf("IP=%s RSSI=%d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  return true;
}

static int bestConfiguredNetworkFromScan() {
  int found = WiFi.scanNetworks();
  Serial.printf("WiFi scan found %d networks\n", found);

  int bestIndex = -1;
  int bestRssi = -1000;
  for (int i = 0; i < found; i++) {
    const String scannedSsid = WiFi.SSID(i);
    Serial.printf("  SSID[%d]=%s RSSI=%d CH=%d ENC=%d\n",
                  i, scannedSsid.c_str(), WiFi.RSSI(i),
                  WiFi.channel(i), WiFi.encryptionType(i));
    for (size_t j = 0; j < WIFI_CREDENTIALS_COUNT; j++) {
      if (validWifiCredential(j) &&
          scannedSsid == WIFI_CREDENTIALS[j].ssid &&
          WiFi.RSSI(i) > bestRssi) {
        bestIndex = static_cast<int>(j);
        bestRssi = WiFi.RSSI(i);
      }
    }
  }
  WiFi.scanDelete();
  return bestIndex;
}

static void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  esp_wifi_set_ps(WIFI_PS_NONE);

  int savedIndex = prefs.getInt("wifi_i", -1);
  if (savedIndex >= 0 && validWifiCredential(static_cast<size_t>(savedIndex))) {
    Serial.printf("Trying saved WiFi profile %d\n", savedIndex);
    if (connectWifiCredential(static_cast<size_t>(savedIndex))) return;
  }

  int bestIndex = bestConfiguredNetworkFromScan();
  if (bestIndex >= 0 && connectWifiCredential(static_cast<size_t>(bestIndex))) return;

  Serial.println("No configured WiFi found; trying all saved profiles");
  for (size_t i = 0; i < WIFI_CREDENTIALS_COUNT; i++) {
    if (static_cast<int>(i) == savedIndex || static_cast<int>(i) == bestIndex) continue;
    if (connectWifiCredential(i)) return;
  }

  Serial.println("WiFi failed");
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
