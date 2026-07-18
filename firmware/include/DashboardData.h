#pragma once

#include <Arduino.h>

static const uint16_t EINK_FRAME_WIDTH = 400;
static const uint16_t EINK_FRAME_HEIGHT = 300;
static const size_t EINK_PLANE_BYTES =
    (static_cast<size_t>(EINK_FRAME_WIDTH) * EINK_FRAME_HEIGHT) / 8;

struct FrameManifest {
  String version;
  String url;
  String crc32Hex;
  uint32_t crc32 = 0;
  uint16_t width = EINK_FRAME_WIDTH;
  uint16_t height = EINK_FRAME_HEIGHT;
  uint16_t refreshSeconds = 300;
  uint32_t bytes = 0;
};

struct EInkFrame {
  uint8_t black[EINK_PLANE_BYTES];
  uint8_t red[EINK_PLANE_BYTES];
  uint32_t crc32 = 0;
};
