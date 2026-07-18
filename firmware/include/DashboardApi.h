#pragma once

#include <Arduino.h>
#include "DashboardData.h"

class DashboardApi {
 public:
  bool fetchManifest(FrameManifest& manifest, String& error);
  bool fetchFrame(const FrameManifest& manifest, EInkFrame& frame, String& error);
};
