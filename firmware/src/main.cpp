#include <Arduino.h>
#include <DNSServer.h>
#include <Preferences.h>
#include <SPI.h>
#include <WiFi.h>
#include <WebServer.h>
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
DNSServer dnsServer;
WebServer configServer(80);

uint32_t nextRefreshAt = 0;
uint16_t localRefreshSeconds = DEFAULT_REFRESH_SECONDS;
String lastFrameCrc;
String customWifiSsid;
String customWifiPassword;

static const uint16_t REFRESH_OPTIONS[] = {60, 300, 600, 900, 1800, 3600};
static const size_t REFRESH_OPTIONS_COUNT = sizeof(REFRESH_OPTIONS) / sizeof(REFRESH_OPTIONS[0]);
static const uint32_t LONG_PRESS_MS = 2500;
static const uint32_t CONFIG_PORTAL_TIMEOUT_MS = 300000;
static const byte DNS_PORT = 53;

#ifndef CONFIG_PORTAL_AP_SSID
#define CONFIG_PORTAL_AP_SSID "ESP32-Dashboard"
#endif

#ifndef CONFIG_PORTAL_AP_PASSWORD
#define CONFIG_PORTAL_AP_PASSWORD "configure"
#endif

static uint16_t effectiveRefreshSeconds() {
  if (manifest.refreshSeconds > 0) return manifest.refreshSeconds;
  return localRefreshSeconds;
}

static void loadPreferences() {
  prefs.begin("dashboard", false);
  localRefreshSeconds = prefs.getUShort("refresh_s", DEFAULT_REFRESH_SECONDS);
  lastFrameCrc = prefs.getString("frame_crc", "");
  customWifiSsid = prefs.getString("wifi_ssid", "");
  customWifiPassword = prefs.getString("wifi_pass", "");
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

static String htmlEscape(const String& value) {
  String out;
  out.reserve(value.length());
  for (size_t i = 0; i < value.length(); i++) {
    char c = value[i];
    if (c == '&') out += "&amp;";
    else if (c == '<') out += "&lt;";
    else if (c == '>') out += "&gt;";
    else if (c == '"') out += "&quot;";
    else out += c;
  }
  return out;
}

static void sendConfigPage(const String& message = "") {
  String page =
      "<!doctype html><html><head><meta charset='utf-8'>"
      "<meta name='viewport' content='width=device-width,initial-scale=1'>"
      "<title>ESP32 Dashboard Wi-Fi</title>"
      "<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:28px;background:#f4efe6;color:#29241f}"
      "main{max-width:420px;margin:auto}input,button{width:100%;box-sizing:border-box;font-size:17px;padding:12px;margin:8px 0}"
      "button{background:#29241f;color:#fff;border:0;border-radius:8px}input{border:1px solid #b8ac9b;border-radius:8px}"
      ".msg{padding:10px;border-left:4px solid #b5573a;background:#fff7ef}</style></head><body><main>"
      "<h2>AI Dashboard Wi-Fi</h2>"
      "<p>Enter the Wi-Fi this ESP32 should use. After saving, the device will reboot and refresh the e-ink screen.</p>";
  if (message.length() > 0) page += "<p class='msg'>" + htmlEscape(message) + "</p>";
  page +=
      "<form method='POST' action='/save'>"
      "<label>Wi-Fi SSID</label>"
      "<input name='ssid' required maxlength='32' value='" + htmlEscape(customWifiSsid) + "'>"
      "<label>Wi-Fi Password</label>"
      "<input name='password' type='password' maxlength='64' value='" + htmlEscape(customWifiPassword) + "'>"
      "<button type='submit'>Save and Reboot</button>"
      "</form>"
      "<p>Fallback built-in profiles remain available if this network is not reachable.</p>"
      "</main></body></html>";
  configServer.send(200, "text/html; charset=utf-8", page);
}

static void startConfigPortal() {
  Serial.println("Starting WiFi config portal");
  WiFi.disconnect(true, true);
  delay(300);
  WiFi.mode(WIFI_AP);

  const char* apPassword = CONFIG_PORTAL_AP_PASSWORD;
  bool apStarted = false;
  if (strlen(apPassword) >= 8) {
    apStarted = WiFi.softAP(CONFIG_PORTAL_AP_SSID, apPassword);
  } else {
    apStarted = WiFi.softAP(CONFIG_PORTAL_AP_SSID);
  }
  if (!apStarted) {
    Serial.println("Config portal AP failed to start");
    return;
  }

  IPAddress apIp = WiFi.softAPIP();
  dnsServer.start(DNS_PORT, "*", apIp);
  configServer.on("/", HTTP_GET, []() { sendConfigPage(); });
  configServer.on("/generate_204", HTTP_GET, []() { sendConfigPage(); });
  configServer.on("/hotspot-detect.html", HTTP_GET, []() { sendConfigPage(); });
  configServer.onNotFound([]() { sendConfigPage(); });
  configServer.on("/save", HTTP_POST, []() {
    String ssid = configServer.arg("ssid");
    String password = configServer.arg("password");
    ssid.trim();
    if (ssid.length() == 0) {
      sendConfigPage("SSID cannot be empty.");
      return;
    }
    prefs.putString("wifi_ssid", ssid);
    prefs.putString("wifi_pass", password);
    prefs.putInt("wifi_i", -1);
    configServer.send(200, "text/html; charset=utf-8",
                      "<!doctype html><html><head><meta charset='utf-8'>"
                      "<meta name='viewport' content='width=device-width,initial-scale=1'></head>"
                      "<body><h2>Saved.</h2><p>ESP32 is rebooting. You can reconnect to your normal Wi-Fi now.</p></body></html>");
    delay(800);
    ESP.restart();
  });
  configServer.begin();

  Serial.printf("Config portal ready: AP=%s IP=%s password=%s timeout=%lus\n",
                CONFIG_PORTAL_AP_SSID, apIp.toString().c_str(),
                strlen(apPassword) >= 8 ? apPassword : "(open)",
                CONFIG_PORTAL_TIMEOUT_MS / 1000UL);

  uint32_t started = millis();
  while (millis() - started < CONFIG_PORTAL_TIMEOUT_MS) {
    dnsServer.processNextRequest();
    configServer.handleClient();
    delay(5);
  }

  Serial.println("Config portal timeout; rebooting");
  ESP.restart();
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

static bool connectCustomWifiCredential() {
  customWifiSsid = prefs.getString("wifi_ssid", "");
  customWifiPassword = prefs.getString("wifi_pass", "");
  customWifiSsid.trim();
  if (customWifiSsid.length() == 0) return false;

  WiFi.disconnect(false, false);
  delay(100);
  WiFi.begin(customWifiSsid.c_str(), customWifiPassword.c_str());
  Serial.printf("WiFi custom SSID=%s", customWifiSsid.c_str());

  if (!waitForWifi(16000)) return false;

  prefs.putInt("wifi_i", -1);
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

  if (connectCustomWifiCredential()) return;

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
  if (digitalRead(PIN_SIDE_BUTTON) == LOW) {
    Serial.println("Button held at boot; entering config portal");
    startConfigPortal();
  }
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
    startConfigPortal();
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
