#pragma once

#include "DashboardData.h"
#include "DisplayConfig.h"

class DashboardUI {
 public:
  explicit DashboardUI(DashboardDisplay& display) : display_(display) {}
  void begin();
  void renderFrame(const EInkFrame& frame);
  void renderStatus(const String& title, const String& detail);

 private:
  DashboardDisplay& display_;

  static bool bitIsSet(const uint8_t* plane, uint16_t x, uint16_t y);
};
