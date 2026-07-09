#pragma once

#include <GxEPD2_3C.h>

#include "config.h"

// Confirmed 4.2 inch tri-color e-paper panel: GDEY042Z98, 400 x 300, SSD1683.
// Common alternatives, if a later batch differs: GxEPD2_420c and GxEPD2_420c_Z21.
using DashboardPanel = GxEPD2_420c_GDEY042Z98;
using DashboardDisplay = GxEPD2_3C<DashboardPanel, DashboardPanel::HEIGHT>;

static const int16_t SCREEN_W = 400;
static const int16_t SCREEN_H = 300;
