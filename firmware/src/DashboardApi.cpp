#include "DashboardApi.h"

#include <ArduinoJson.h>
#include <WiFiClient.h>

#include "config.h"

static uint16_t readLe16(const uint8_t* data) {
  return static_cast<uint16_t>(data[0]) |
         (static_cast<uint16_t>(data[1]) << 8);
}

static uint32_t readLe32(const uint8_t* data) {
  return static_cast<uint32_t>(data[0]) |
         (static_cast<uint32_t>(data[1]) << 8) |
         (static_cast<uint32_t>(data[2]) << 16) |
         (static_cast<uint32_t>(data[3]) << 24);
}

static uint32_t parseHex32(const String& value) {
  uint32_t out = 0;
  for (size_t i = 0; i < value.length(); i++) {
    char c = value[i];
    uint8_t nibble;
    if (c >= '0' && c <= '9') nibble = c - '0';
    else if (c >= 'a' && c <= 'f') nibble = c - 'a' + 10;
    else if (c >= 'A' && c <= 'F') nibble = c - 'A' + 10;
    else continue;
    out = (out << 4) | nibble;
  }
  return out;
}

static uint32_t crc32Update(uint32_t crc, const uint8_t* data, size_t len) {
  crc = ~crc;
  for (size_t i = 0; i < len; i++) {
    crc ^= data[i];
    for (uint8_t bit = 0; bit < 8; bit++) {
      crc = (crc >> 1) ^ (0xEDB88320UL & (0UL - (crc & 1UL)));
    }
  }
  return ~crc;
}

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

static bool openHttpGet(WiFiClient& client, const char* path, const char* accept,
                        int& contentLength, String& error) {
  client.setTimeout(120);
  contentLength = -1;

  Serial.printf("GET http://%s%s\n", DASHBOARD_API_HOST, path);
  if (!client.connect(DASHBOARD_API_HOST, DASHBOARD_API_PORT, 20000)) {
    error = "HTTP TCP connect failed";
    return false;
  }
  client.setNoDelay(true);

  client.printf("GET %s HTTP/1.1\r\n", path);
  client.printf("Host: %s\r\n", DASHBOARD_API_HOST);
  client.print("User-Agent: esp32-ai-dashboard/2.0\r\n");
  client.printf("Accept: %s\r\n", accept);
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

  while (readHttpLine(client, line, 30000)) {
    if (line.length() == 0) break;
    if (line.startsWith("Content-Length:") || line.startsWith("content-length:")) {
      contentLength = line.substring(line.indexOf(':') + 1).toInt();
    }
  }
  return true;
}

static bool readTextBody(WiFiClient& client, String& body, int contentLength,
                         uint32_t timeoutMs, String& error) {
  body = "";
  body.reserve(contentLength > 0 ? contentLength + 1 : 512);

  uint32_t start = millis();
  while (millis() - start < timeoutMs) {
    while (client.available()) {
      body += static_cast<char>(client.read());
      if (contentLength >= 0 && body.length() >= static_cast<size_t>(contentLength)) {
        return true;
      }
      if (body.length() > 4096) {
        error = "HTTP text body too large";
        return false;
      }
    }
    if (contentLength < 0 && !client.connected()) return body.length() > 0;
    delay(5);
  }
  error = "HTTP text timeout " + String(body.length()) + "/" + String(contentLength);
  return false;
}

static bool readExact(WiFiClient& client, uint8_t* out, size_t len,
                      uint32_t timeoutMs, String& error) {
  size_t got = 0;
  uint32_t start = millis();
  while (millis() - start < timeoutMs) {
    while (client.available() && got < len) {
      got += client.read(out + got, len - got);
      if (got >= len) return true;
    }
    if (!client.connected() && !client.available()) break;
    delay(5);
  }
  error = "HTTP binary short read " + String(got) + "/" + String(len);
  return false;
}

bool DashboardApi::fetchManifest(FrameManifest& manifest, String& error) {
  for (uint8_t attempt = 1; attempt <= 5; attempt++) {
    Serial.printf("Manifest attempt %u/5\n", attempt);
    WiFiClient client;
    int contentLength = -1;
    if (!openHttpGet(client, DASHBOARD_MANIFEST_PATH, "application/json",
                     contentLength, error)) {
      delay(2000);
      continue;
    }

    String payload;
    bool ok = readTextBody(client, payload, contentLength, 30000, error);
    client.stop();
    if (!ok) {
      delay(2000);
      continue;
    }

    JsonDocument doc;
    DeserializationError jsonError = deserializeJson(doc, payload);
    if (jsonError) {
      error = jsonError.c_str();
      return false;
    }

    manifest.version = String(doc["version"] | "");
    manifest.url = String(doc["url"] | DASHBOARD_FRAME_PATH);
    manifest.crc32Hex = String(doc["crc32"] | "");
    manifest.crc32 = parseHex32(manifest.crc32Hex);
    manifest.width = doc["width"] | 0;
    manifest.height = doc["height"] | 0;
    manifest.refreshSeconds = doc["refresh_interval"] | DEFAULT_REFRESH_SECONDS;
    manifest.bytes = doc["bytes"] | 0;

    if (manifest.width != EINK_FRAME_WIDTH || manifest.height != EINK_FRAME_HEIGHT) {
      error = "Bad manifest size";
      return false;
    }
    if (manifest.url.length() == 0 || manifest.crc32 == 0) {
      error = "Manifest missing frame url/crc";
      return false;
    }
    Serial.printf("Manifest ok version=%s crc=%s bytes=%lu refresh=%us\n",
                  manifest.version.c_str(), manifest.crc32Hex.c_str(),
                  static_cast<unsigned long>(manifest.bytes),
                  manifest.refreshSeconds);
    return true;
  }
  return false;
}

bool DashboardApi::fetchFrame(const FrameManifest& manifest, EInkFrame& frame,
                              String& error) {
  const String path = manifest.url.length() ? manifest.url : String(DASHBOARD_FRAME_PATH);

  for (uint8_t attempt = 1; attempt <= 5; attempt++) {
    Serial.printf("Frame attempt %u/5\n", attempt);
    WiFiClient client;
    int contentLength = -1;
    if (!openHttpGet(client, path.c_str(), "application/octet-stream",
                     contentLength, error)) {
      delay(2000);
      continue;
    }

    static const size_t HEADER_LEN = 26;
    uint8_t header[HEADER_LEN];
    if (!readExact(client, header, HEADER_LEN, 30000, error)) {
      client.stop();
      delay(2000);
      continue;
    }

    if (memcmp(header, "EINK3C01", 8) != 0) {
      error = "Bad frame magic";
      client.stop();
      return false;
    }
    const uint16_t width = readLe16(header + 8);
    const uint16_t height = readLe16(header + 10);
    const uint32_t blackLen = readLe32(header + 14);
    const uint32_t redLen = readLe32(header + 18);
    const uint32_t payloadCrc = readLe32(header + 22);

    if (width != EINK_FRAME_WIDTH || height != EINK_FRAME_HEIGHT ||
        blackLen != EINK_PLANE_BYTES || redLen != EINK_PLANE_BYTES) {
      error = "Bad frame geometry";
      client.stop();
      return false;
    }
    if (contentLength >= 0 && contentLength != static_cast<int>(HEADER_LEN + blackLen + redLen)) {
      error = "Bad frame content length";
      client.stop();
      return false;
    }

    if (!readExact(client, frame.black, EINK_PLANE_BYTES, 120000, error) ||
        !readExact(client, frame.red, EINK_PLANE_BYTES, 120000, error)) {
      client.stop();
      delay(2000);
      continue;
    }
    client.stop();

    uint32_t crc = 0;
    crc = crc32Update(crc, frame.black, EINK_PLANE_BYTES);
    crc = crc32Update(crc, frame.red, EINK_PLANE_BYTES);
    if (crc != payloadCrc || crc != manifest.crc32) {
      error = "CRC mismatch";
      Serial.printf("crc got=%08lx header=%08lx manifest=%08lx\n",
                    static_cast<unsigned long>(crc),
                    static_cast<unsigned long>(payloadCrc),
                    static_cast<unsigned long>(manifest.crc32));
      return false;
    }

    frame.crc32 = crc;
    Serial.printf("Frame ok crc=%08lx\n", static_cast<unsigned long>(frame.crc32));
    return true;
  }
  return false;
}
