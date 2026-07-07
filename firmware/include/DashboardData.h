#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

static const size_t MAX_AI_CARDS = 2;
static const size_t MAX_TODOS = 7;
static const size_t MAX_NOTES = 3;

struct MetaData {
  String title;
  String time;
  String date;
  String lastUpdate;
  uint16_t refreshSeconds = 300;
  bool hasServerRefreshInterval = false;
  int wifiRssi = 0;
  uint8_t batteryPercent = 0;
  String version;
};

struct AiUsage {
  String id;
  String label;
  String accent;
  String plan;
  uint8_t dailyPercent = 0;
  String dailyReset;
  String dailyDelta;
  uint8_t weeklyPercent = 0;
  String weeklyReset;
  String weeklyDelta;
  String model;
  String todayUsed;
  String todayDelta;
  uint16_t requests = 0;
  String requestDelta;
};

struct ServerStatus {
  uint8_t cpuPercent = 0;
  uint8_t ramPercent = 0;
  uint8_t diskPercent = 0;
  String status;
  String loadAvg;
  String uptime;
};

struct WeatherData {
  String tempC;
  String feelsLikeC;
  uint8_t humidityPercent = 0;
  String wind;
  int trend[10] = {0};
  size_t trendCount = 0;
};

struct TodoItem {
  String text;
  String due;
  bool done = false;
};

struct DashboardData {
  MetaData meta;
  AiUsage ai[MAX_AI_CARDS];
  size_t aiCount = 0;
  ServerStatus server;
  WeatherData weather;
  TodoItem todos[MAX_TODOS];
  size_t todoCount = 0;
  String notes[MAX_NOTES];
  size_t noteCount = 0;
};

bool parseDashboardJson(const String& json, DashboardData& out, String& error);
