#include "DashboardUI.h"

#include <Fonts/FreeMonoBold9pt7b.h>
#include <Fonts/FreeSans9pt7b.h>

static const uint16_t BLACK = GxEPD_BLACK;
static const uint16_t WHITE = GxEPD_WHITE;
static const uint16_t RED = GxEPD_RED;

void DashboardUI::begin() {
  display_.init(115200, true, 2, false);
  display_.setRotation(0);
  display_.hibernate();
}

bool DashboardUI::bitIsSet(const uint8_t* plane, uint16_t x, uint16_t y) {
  const size_t bitIndex = static_cast<size_t>(y) * EINK_FRAME_WIDTH + x;
  const uint8_t mask = 0x80 >> (bitIndex & 7);
  return (plane[bitIndex >> 3] & mask) != 0;
}

void DashboardUI::renderFrame(const EInkFrame& frame) {
  display_.setFullWindow();
  display_.firstPage();
  do {
    display_.fillScreen(WHITE);
    for (uint16_t y = 0; y < EINK_FRAME_HEIGHT; y++) {
      for (uint16_t x = 0; x < EINK_FRAME_WIDTH; x++) {
        if (bitIsSet(frame.red, x, y)) {
          display_.drawPixel(x, y, RED);
        } else if (bitIsSet(frame.black, x, y)) {
          display_.drawPixel(x, y, BLACK);
        }
      }
    }
  } while (display_.nextPage());
  display_.hibernate();
}

void DashboardUI::renderStatus(const String& title, const String& detail) {
  display_.setFullWindow();
  display_.firstPage();
  do {
    display_.fillScreen(WHITE);
    display_.setTextColor(RED);
    display_.setFont(&FreeMonoBold9pt7b);
    display_.setCursor(18, 42);
    display_.print(title);

    display_.setTextColor(BLACK);
    display_.setFont(&FreeSans9pt7b);
    display_.setCursor(18, 82);
    display_.print(detail);
    display_.setCursor(18, 122);
    display_.print("Server-rendered frame mode");
    display_.setCursor(18, 158);
    display_.print("GET /render/eink.bin");
  } while (display_.nextPage());
  display_.hibernate();
}
