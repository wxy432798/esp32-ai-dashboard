#include "DashboardApi.h"

#include <HTTPClient.h>
#include <WiFiClient.h>

#include "config.h"

bool DashboardApi::fetch(DashboardData& out, String& error) {
  WiFiClient client;
  HTTPClient http;
  http.setTimeout(12000);

  if (!http.begin(client, DASHBOARD_API_URL)) {
    error = "http.begin failed";
    return false;
  }

  int code = http.GET();
  if (code != HTTP_CODE_OK) {
    error = "HTTP " + String(code);
    http.end();
    return false;
  }

  String payload = http.getString();
  http.end();
  return parseDashboardJson(payload, out, error);
}

