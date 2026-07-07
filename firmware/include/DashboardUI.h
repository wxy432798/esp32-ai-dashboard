#pragma once

#include "DashboardData.h"
#include "DisplayConfig.h"

class DashboardUI {
 public:
  explicit DashboardUI(DashboardDisplay& display) : display_(display) {}
  void begin();
  void render(const DashboardData& data, const String& statusLine = "");

 private:
  DashboardDisplay& display_;

  void drawFrame(const DashboardData& data, const String& statusLine);
  void drawAiCard(int16_t x, int16_t y, int16_t w, int16_t h, const AiUsage& ai);
  void drawServerCard(int16_t x, int16_t y, int16_t w, int16_t h, const ServerStatus& server);
  void drawWeatherCard(int16_t x, int16_t y, int16_t w, int16_t h, const WeatherData& weather);
  void drawTodoCard(int16_t x, int16_t y, int16_t w, int16_t h, const DashboardData& data);
  void drawNotesCard(int16_t x, int16_t y, int16_t w, int16_t h, const DashboardData& data);
  void drawProgress(int16_t x, int16_t y, int16_t w, int16_t h, uint8_t percent, uint16_t color);
  void drawMetricBar(int16_t x, int16_t y, const char* label, uint8_t percent);
  void drawTrend(int16_t x, int16_t y, int16_t w, int16_t h, const WeatherData& weather);
  void text(int16_t x, int16_t y, const String& value, uint16_t color, uint8_t size = 1);
};
