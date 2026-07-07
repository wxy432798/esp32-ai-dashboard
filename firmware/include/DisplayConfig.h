#pragma once

#include <GxEPD2_3C.h>
#include <GxEPD2_BW.h>

#include "config.h"

// Most 4.2 inch tri-color e-paper modules are 400 x 300.
// If your actual panel uses a different controller, replace this driver alias.
//
// Common alternatives in GxEPD2 include GxEPD2_420c and GxEPD2_420c_Z21.
using DashboardDisplay = GxEPD2_3C<GxEPD2_420c, GxEPD2_420c::HEIGHT>;

static const int16_t SCREEN_W = 400;
static const int16_t SCREEN_H = 300;

