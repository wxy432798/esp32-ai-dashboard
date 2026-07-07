#include "DashboardUI.h"

#include <Fonts/FreeMono9pt7b.h>
#include <Fonts/FreeMonoBold9pt7b.h>
#include <Fonts/FreeMonoBold12pt7b.h>

static const uint16_t BLACK = GxEPD_BLACK;
static const uint16_t WHITE = GxEPD_WHITE;
static const uint16_t RED = GxEPD_RED;

void DashboardUI::begin() {
  display_.init(115200, true, 2, false);
  display_.setRotation(1);
}

void DashboardUI::render(const DashboardData& data, const String& statusLine) {
  display_.setFullWindow();
  display_.firstPage();
  do {
    display_.fillScreen(WHITE);
    drawFrame(data, statusLine);
    drawAiCard(6, 28, 196, 84, data.ai[0]);
    if (data.aiCount > 1) drawAiCard(6, 116, 196, 84, data.ai[1]);
    drawServerCard(6, 204, 196, 34, data.server);
    drawWeatherCard(6, 242, 196, 42, data.weather);
    drawTodoCard(208, 28, 186, 160, data);
    drawNotesCard(208, 192, 186, 92, data);
  } while (display_.nextPage());
}

void DashboardUI::drawFrame(const DashboardData& data, const String& statusLine) {
  display_.drawRoundRect(2, 2, SCREEN_W - 4, SCREEN_H - 4, 4, BLACK);
  display_.drawFastHLine(8, 24, SCREEN_W - 16, BLACK);
  display_.setFont(&FreeMonoBold9pt7b);
  text(18, 17, data.meta.title, BLACK);
  text(210, 17, data.meta.time, BLACK);
  text(344, 17, String(data.meta.batteryPercent) + "%", BLACK);
  display_.setFont();
  text(8, 294, "LAST UPDATE", BLACK);
  text(78, 294, data.meta.lastUpdate, BLACK);
  text(240, 294, "AUTO REFRESH", BLACK);
  text(328, 294, String(data.meta.refreshSeconds / 60) + " min", BLACK);
  text(368, 294, data.meta.version, BLACK);
  if (statusLine.length()) text(8, 286, statusLine, RED);
}

void DashboardUI::drawAiCard(int16_t x, int16_t y, int16_t w, int16_t h, const AiUsage& ai) {
  uint16_t accent = ai.accent == "red" ? RED : BLACK;
  display_.drawRoundRect(x, y, w, h, 4, BLACK);
  display_.setFont(&FreeMonoBold12pt7b);
  text(x + 8, y + 18, ai.label, BLACK);
  display_.setFont();
  display_.drawRoundRect(x + w - 28, y + 8, 22, 12, 2, accent);
  text(x + w - 24, y + 18, ai.plan, accent);
  text(x + 8, y + 34, "Daily", BLACK);
  text(x + 106, y + 34, "Weekly", BLACK);
  display_.setFont(&FreeMonoBold12pt7b);
  text(x + 8, y + 52, String(ai.dailyPercent) + "%", accent);
  text(x + 106, y + 52, String(ai.weeklyPercent) + "%", accent);
  display_.setFont();
  drawProgress(x + 8, y + 58, 82, 5, ai.dailyPercent, accent);
  drawProgress(x + 106, y + 58, 82, 5, ai.weeklyPercent, accent);
  text(x + 8, y + 73, "Reset " + ai.dailyReset, BLACK);
  text(x + 106, y + 73, "Reset " + ai.weeklyReset, BLACK);
  text(x + 8, y + 82, ai.model, accent);
  text(x + 70, y + 82, ai.todayUsed, accent);
  text(x + 138, y + 82, String(ai.requests), accent);
}

void DashboardUI::drawServerCard(int16_t x, int16_t y, int16_t w, int16_t h, const ServerStatus& server) {
  display_.drawRoundRect(x, y, w, h, 4, BLACK);
  text(x + 8, y + 12, "SERVER STATUS", BLACK);
  drawMetricBar(x + 8, y + 22, "CPU", server.cpuPercent);
  drawMetricBar(x + 70, y + 22, "RAM", server.ramPercent);
  drawMetricBar(x + 132, y + 22, "DSK", server.diskPercent);
  text(x + 132, y + 12, server.status, RED);
}

void DashboardUI::drawWeatherCard(int16_t x, int16_t y, int16_t w, int16_t h, const WeatherData& weather) {
  display_.drawRoundRect(x, y, w, h, 4, BLACK);
  display_.setFont(&FreeMonoBold12pt7b);
  text(x + 8, y + 26, weather.tempC + "C", RED);
  display_.setFont();
  text(x + 8, y + 36, "Feels " + weather.feelsLikeC + "C", BLACK);
  text(x + 76, y + 18, "Humidity " + String(weather.humidityPercent) + "%", BLACK);
  text(x + 76, y + 34, "Wind " + weather.wind, BLACK);
  drawTrend(x + 146, y + 10, 42, 26, weather);
}

void DashboardUI::drawTodoCard(int16_t x, int16_t y, int16_t w, int16_t h, const DashboardData& data) {
  display_.drawRoundRect(x, y, w, h, 4, BLACK);
  display_.setFont(&FreeMonoBold9pt7b);
  text(x + 8, y + 18, "TO-DO LIST", BLACK);
  display_.setFont();
  text(x + w - 28, y + 18, String(data.todoCount) + "/7", BLACK);
  int16_t rowY = y + 36;
  for (size_t i = 0; i < data.todoCount; i++) {
    const TodoItem& todo = data.todos[i];
    display_.drawRect(x + 8, rowY - 10, 9, 9, todo.done ? RED : BLACK);
    if (todo.done) {
      display_.drawLine(x + 10, rowY - 6, x + 12, rowY - 3, RED);
      display_.drawLine(x + 12, rowY - 3, x + 17, rowY - 10, RED);
    }
    text(x + 24, rowY, todo.text.substring(0, 18), BLACK);
    text(x + w - 28, rowY, todo.due, BLACK);
    display_.drawFastHLine(x + 6, rowY + 8, w - 12, BLACK);
    rowY += 20;
  }
}

void DashboardUI::drawNotesCard(int16_t x, int16_t y, int16_t w, int16_t h, const DashboardData& data) {
  display_.drawRoundRect(x, y, w, h, 4, BLACK);
  display_.setFont(&FreeMonoBold9pt7b);
  text(x + 8, y + 18, "NOTES", BLACK);
  display_.setFont();
  if (data.noteCount) text(x + 8, y + 30, data.notes[0], BLACK);
}

void DashboardUI::drawProgress(int16_t x, int16_t y, int16_t w, int16_t h, uint8_t percent, uint16_t color) {
  display_.drawRect(x, y, w, h, BLACK);
  int16_t fillW = map(constrain(percent, 0, 100), 0, 100, 0, w - 2);
  display_.fillRect(x + 1, y + 1, fillW, h - 2, color);
}

void DashboardUI::drawMetricBar(int16_t x, int16_t y, const char* label, uint8_t percent) {
  text(x, y, label, BLACK);
  display_.drawRect(x + 22, y - 7, 28, 5, BLACK);
  display_.fillRect(x + 23, y - 6, map(constrain(percent, 0, 100), 0, 100, 0, 26), 3, BLACK);
}

void DashboardUI::drawTrend(int16_t x, int16_t y, int16_t w, int16_t h, const WeatherData& weather) {
  if (weather.trendCount < 2) return;
  int minV = weather.trend[0];
  int maxV = weather.trend[0];
  for (size_t i = 1; i < weather.trendCount; i++) {
    minV = min(minV, weather.trend[i]);
    maxV = max(maxV, weather.trend[i]);
  }
  if (minV == maxV) maxV = minV + 1;
  for (size_t i = 1; i < weather.trendCount; i++) {
    int16_t x1 = x + map(i - 1, 0, weather.trendCount - 1, 0, w);
    int16_t x2 = x + map(i, 0, weather.trendCount - 1, 0, w);
    int16_t y1 = y + h - map(weather.trend[i - 1], minV, maxV, 0, h);
    int16_t y2 = y + h - map(weather.trend[i], minV, maxV, 0, h);
    display_.drawLine(x1, y1, x2, y2, RED);
  }
}

void DashboardUI::text(int16_t x, int16_t y, const String& value, uint16_t color, uint8_t size) {
  display_.setTextColor(color);
  display_.setTextSize(size);
  display_.setCursor(x, y);
  display_.print(value);
}
