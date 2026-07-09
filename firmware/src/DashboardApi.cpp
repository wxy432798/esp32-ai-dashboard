#include "DashboardApi.h"

#include <WiFiClient.h>

#include "config.h"

static bool readHttpLine(WiFiClient& client, String& line, uint32_t timeoutMs) {
  line = "";
  uint32_t start = millis();
  while (millis() - start < timeoutMs) {
    while (client.available()) {
      char c = static_cast<char>(client.read());
      if (c == '\n') {
        line.trim();
        return true;
      }
      line += c;
      if (line.length() > 256) return false;
    }
    if (!client.connected() && !client.available()) return line.length() > 0;
    delay(5);
  }
  return false;
}

static bool readHttpBody(WiFiClient& client, String& body, int contentLength,
                         uint32_t timeoutMs, String& error) {
  body = "";
  body.reserve(contentLength > 0 ? contentLength + 1 : 2048);

  uint32_t start = millis();
  while (millis() - start < timeoutMs) {
    while (client.available()) {
      body += static_cast<char>(client.read());
      if (contentLength >= 0 && body.length() >= static_cast<size_t>(contentLength)) {
        return true;
      }
      if (body.length() > 4096) {
        error = "HTTP body too large";
        return false;
      }
    }
    if (contentLength < 0 && !client.connected()) return body.length() > 0;
    delay(5);
  }

  error = "HTTP body timeout " + String(body.length()) + "/" + String(contentLength);
  return false;
}

static bool httpGetBodyOnce(const char* path, String& body, String& error) {
  WiFiClient client;
  client.setTimeout(30);

  Serial.printf("GET http://%s%s\n", DASHBOARD_API_HOST, path);
  if (!client.connect(DASHBOARD_API_HOST, DASHBOARD_API_PORT, 20000)) {
    error = "HTTP TCP connect failed";
    return false;
  }
  client.setNoDelay(true);

  client.printf("GET %s HTTP/1.1\r\n", path);
  client.printf("Host: %s\r\n", DASHBOARD_API_HOST);
  client.print("User-Agent: esp32-ai-dashboard/1.0\r\n");
  client.print("Accept: application/json\r\n");
  client.print("Accept-Encoding: identity\r\n");
  client.print("Connection: close\r\n");
  if (String(ESP32_API_KEY).length() > 0) {
    client.printf("X-API-Key: %s\r\n", ESP32_API_KEY);
  }
  client.print("\r\n");
  client.flush();

  String line;
  if (!readHttpLine(client, line, 30000)) {
    error = "HTTP status read failed";
    client.stop();
    return false;
  }
  Serial.println(line);
  if (!line.startsWith("HTTP/1.") || line.indexOf(" 200 ") < 0) {
    error = "Bad HTTP status: " + line;
    client.stop();
    return false;
  }

  int contentLength = -1;
  while (readHttpLine(client, line, 30000)) {
    if (line.length() == 0) break;
    if (line.startsWith("Content-Length:") || line.startsWith("content-length:")) {
      contentLength = line.substring(line.indexOf(':') + 1).toInt();
    }
  }

  if (!readHttpBody(client, body, contentLength, 30000, error)) {
    client.stop();
    return false;
  }
  client.stop();
  Serial.printf("HTTP body bytes=%u\n", static_cast<unsigned>(body.length()));
  return true;
}

static bool httpGetBody(const char* path, String& body, String& error) {
  for (uint8_t attempt = 1; attempt <= 5; attempt++) {
    Serial.printf("HTTP attempt %u/5\n", attempt);
    if (httpGetBodyOnce(path, body, error)) return true;
    delay(2000);
  }
  return false;
}

bool DashboardApi::fetch(DashboardData& out, String& error) {
  Serial.printf("Dashboard URL %s\n", DASHBOARD_API_URL);
  String payload;
  if (!httpGetBody(DASHBOARD_API_PATH, payload, error)) {
    return false;
  }
  return parseDashboardJson(payload, out, error);
}
