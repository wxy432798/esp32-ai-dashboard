#include "DashboardData.h"

static String asString(JsonVariantConst v, const char* fallback = "") {
  if (v.isNull()) return String(fallback);
  if (v.is<const char*>()) return String(v.as<const char*>());
  if (v.is<float>() || v.is<double>()) return String(v.as<float>(), 1);
  if (v.is<int>()) return String(v.as<int>());
  return String(fallback);
}

static String updatedTime(const String& updatedAt) {
  int space = updatedAt.indexOf(' ');
  if (space >= 0 && updatedAt.length() >= space + 6) return updatedAt.substring(space + 1, space + 6);
  return "--:--";
}

static String updatedDate(const String& updatedAt) {
  if (updatedAt.length() >= 10) return updatedAt.substring(5, 10);
  return "--";
}

static void parseAiObject(JsonObjectConst item, AiUsage& ai, const char* id, const char* label, const char* accent) {
  ai.id = id;
  ai.label = label;
  ai.accent = accent;
  ai.plan = "";
  ai.dailyPercent = item["daily_percent"] | 0;
  ai.dailyReset = asString(item["daily_reset"]);
  ai.dailyDelta = String(ai.dailyPercent) + "% used today";
  ai.weeklyPercent = item["weekly_percent"] | 0;
  ai.weeklyReset = asString(item["weekly_reset"]);
  ai.weeklyDelta = String(ai.weeklyPercent) + "% used this week";
  ai.model = asString(item["model"]);
  ai.todayUsed = asString(item["used_today"]);
  ai.todayDelta = "";
  ai.requests = item["requests_today"] | 0;
  ai.requestDelta = "";
}

bool parseDashboardJson(const String& json, DashboardData& out, String& error) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, json);
  if (err) {
    error = err.c_str();
    return false;
  }

  String updatedAt = asString(doc["updated_at"]);
  out.meta.title = "AI DASHBOARD";
  out.meta.time = updatedTime(updatedAt);
  out.meta.date = updatedDate(updatedAt);
  out.meta.lastUpdate = updatedAt;
  out.meta.hasServerRefreshInterval = doc["refresh_interval_sec"].is<uint16_t>() && (doc["refresh_interval_sec"] | 0) > 0;
  out.meta.refreshSeconds = doc["refresh_interval_sec"] | 300;
  out.meta.wifiRssi = 0;
  out.meta.batteryPercent = 0;
  out.meta.version = "v1.0.0";

  out.aiCount = 0;
  if (doc["claude"].is<JsonObjectConst>() && out.aiCount < MAX_AI_CARDS) {
    parseAiObject(doc["claude"].as<JsonObjectConst>(), out.ai[out.aiCount++], "claude", "Claude UI", "red");
  }
  if (doc["codex"].is<JsonObjectConst>() && out.aiCount < MAX_AI_CARDS) {
    parseAiObject(doc["codex"].as<JsonObjectConst>(), out.ai[out.aiCount++], "codex", "Codex UI", "black");
  }

  JsonObjectConst server = doc["server"];
  out.server.cpuPercent = server["cpu"] | 0;
  out.server.ramPercent = server["ram"] | 0;
  out.server.diskPercent = server["disk"] | 0;
  out.server.status = (server["online"] | false) ? "ONLINE" : "OFFLINE";
  out.server.loadAvg = asString(server["load_avg"]);
  out.server.uptime = asString(server["uptime"]);

  JsonObjectConst weather = doc["weather"];
  out.weather.tempC = asString(weather["temperature"]);
  out.weather.feelsLikeC = asString(weather["temperature"]);
  out.weather.humidityPercent = weather["humidity"] | 0;
  out.weather.wind = asString(weather["wind"]) + " " + asString(weather["wind_speed"]);
  out.weather.trendCount = 0;

  out.todoCount = 0;
  for (JsonVariantConst raw : doc["todos"].as<JsonArrayConst>()) {
    if (out.todoCount >= MAX_TODOS) break;
    TodoItem& todo = out.todos[out.todoCount++];
    if (raw.is<JsonObjectConst>()) {
      JsonObjectConst item = raw.as<JsonObjectConst>();
      todo.text = asString(item["text"]);
      todo.due = asString(item["due"]);
      todo.done = item["done"] | false;
    } else {
      todo.text = asString(raw);
      todo.due = "";
      todo.done = false;
    }
  }

  out.noteCount = 1;
  out.notes[0] = asString(doc["note"]);

  return true;
}
