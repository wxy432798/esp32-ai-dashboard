#pragma once

#include <Arduino.h>
#include "DashboardData.h"

class DashboardApi {
 public:
  bool fetch(DashboardData& out, String& error);
};

