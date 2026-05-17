#include "display.h"
#include "emoji_bitmaps.h"
#include <M5GFX.h>
#include <M5Unified.h>
#include <lgfx/v1/lgfx_fonts.hpp>
#include <strings.h>

static constexpr int kW = 240;
static constexpr int kH = 135;
static constexpr int kMarginX = 8;
static constexpr int kMarginY = 8;
static constexpr int kStampGap = 4;
static constexpr uint16_t kStampFg = TFT_WHITE;

static void applyRotation(void) { M5.Lcd.setRotation(3); }

/** size 1–4 换 efont；5–6 在 24 号字上放大，便于与 40px emoji 对齐 */
static void applyFontSize(uint8_t size) {
  using namespace lgfx::v1::fonts;
  const lgfx::v1::IFont *font = &efontCN_12;
  float zoom = 1.0f;
  switch (size) {
  case 1:
    font = &efontCN_10;
    break;
  case 2:
    font = &efontCN_12;
    break;
  case 3:
    font = &efontCN_16;
    break;
  case 4:
    font = &efontCN_24;
    break;
  case 5:
    font = &efontCN_24;
    zoom = 1.35f;
    break;
  case 6:
    font = &efontCN_24;
    zoom = 1.7f;
    break;
  default:
    font = &efontCN_24;
    zoom = 1.7f;
    break;
  }
  M5.Lcd.setFont(font);
  M5.Lcd.setTextSize(zoom, zoom);
}

static uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return (uint16_t)(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3));
}

uint16_t displayParseColor(const char *s, uint16_t fallback) {
  if (!s || !s[0])
    return fallback;
  if (s[0] == '#') {
    unsigned long v = strtoul(s + 1, nullptr, 16);
    if (strlen(s) >= 7) {
      uint8_t r = (v >> 16) & 0xFF;
      uint8_t g = (v >> 8) & 0xFF;
      uint8_t b = v & 0xFF;
      return rgb565(r, g, b);
    }
    uint8_t r = ((v >> 8) & 0xF) * 17;
    uint8_t g = ((v >> 4) & 0xF) * 17;
    uint8_t b = (v & 0xF) * 17;
    return rgb565(r, g, b);
  }
  if (!strcasecmp(s, "red"))
    return TFT_RED;
  if (!strcasecmp(s, "green"))
    return TFT_GREEN;
  if (!strcasecmp(s, "yellow"))
    return TFT_YELLOW;
  if (!strcasecmp(s, "blue"))
    return TFT_BLUE;
  if (!strcasecmp(s, "black"))
    return TFT_BLACK;
  if (!strcasecmp(s, "white"))
    return TFT_WHITE;
  return fallback;
}

static uint8_t clampSize(int s) {
  if (s < 1)
    return 1;
  if (s > 6)
    return 6;
  return (uint8_t)s;
}

static uint8_t countNonemptyLines(const char *const *lines, uint8_t lineCount) {
  uint8_t n = 0;
  for (uint8_t i = 0; i < lineCount; i++) {
    if (lines[i] && lines[i][0])
      n++;
  }
  return n;
}

/** 在 maxSz→1 中选能放进 maxW 的最大字号 */
static uint8_t pickFontSizeToFitWidth(const char *text, int maxW,
                                      uint8_t maxSz) {
  maxSz = clampSize(maxSz);
  for (uint8_t sz = maxSz; sz >= 1; --sz) {
    applyFontSize(sz);
    if ((int)M5.Lcd.textWidth(text) <= maxW)
      return sz;
  }
  return 1;
}

static uint8_t pickStampFontSize(const char *text) {
  return pickFontSizeToFitWidth(text, kW - 2 * kMarginX, 5);
}

static int msgTopY(uint8_t sz, bool hasEmoji) {
  applyFontSize(sz);
  const int lineH = M5.Lcd.fontHeight();
  if (!hasEmoji)
    return kMarginY;
  int y = kMarginY + (EMOJI_DRAW_H - lineH) / 2;
  return y < kMarginY ? kMarginY : y;
}

static int msgBlockHeight(uint8_t sz, uint8_t lineCount, uint8_t gap) {
  if (lineCount == 0)
    return 0;
  applyFontSize(sz);
  const int lineH = M5.Lcd.fontHeight();
  if (lineCount == 1)
    return lineH;
  return (int)lineCount * lineH + (int)(lineCount - 1) * gap;
}

/** 主文案：不超过请求字号，且适配宽度与内容区高度 */
static uint8_t pickMsgFontSize(const char *const *lines, uint8_t lineCount,
                               int maxW, int contentBottom, uint8_t maxSz,
                               uint8_t gap, bool hasEmoji) {
  const uint8_t n = countNonemptyLines(lines, lineCount);
  if (n == 0)
    return clampSize(maxSz);

  maxSz = clampSize(maxSz);
  for (uint8_t sz = maxSz; sz >= 1; --sz) {
    bool widthOk = true;
    for (uint8_t i = 0; i < lineCount; i++) {
      if (!lines[i] || !lines[i][0])
        continue;
      applyFontSize(sz);
      if ((int)M5.Lcd.textWidth(lines[i]) > maxW) {
        widthOk = false;
        break;
      }
    }
    if (!widthOk)
      continue;

    const int topY = msgTopY(sz, hasEmoji);
    if (topY + msgBlockHeight(sz, n, gap) <= contentBottom)
      return sz;
  }
  return 1;
}

void displayBegin(void) {
  auto cfg = M5.config();
  cfg.internal_spk = true; /* ES8311；实际 begin 在 audioBegin */
  M5.begin(cfg);
  M5.Display.setBrightness(128);
  displayWaiting();
}

void displayWaiting(void) {
  applyRotation();
  M5.Lcd.fillScreen(TFT_BLACK);
  applyFontSize(3);
  M5.Lcd.setTextColor(TFT_WHITE, TFT_BLACK);
  M5.Lcd.setTextDatum(middle_center);
  M5.Lcd.drawString("等待连接 .oO.oO", kW / 2, kH / 2);
  M5.Lcd.setTextDatum(top_left);
}

void displayLines(const char *const *lines, uint8_t lineCount,
                  const DisplayStyle &style, const char *emojiName,
                  const char *stampText) {
  if (!lineCount || !lines)
    return;

  DisplayStyle st = style;
  st.size = clampSize(st.size);
  if (st.gap > 24)
    st.gap = 24;

  const int8_t emojiId = emojiIdFromName(emojiName);
  const bool hasEmoji = emojiId >= 0;
  const int textX =
      hasEmoji ? (kMarginX + EMOJI_DRAW_W + 6) : kMarginX;
  const int maxW = kW - textX - kMarginX;

  applyRotation();
  M5.Lcd.fillScreen(st.bg);
  M5.Lcd.setTextDatum(top_left);

  int contentBottom = kH - kMarginY;
  int stampY = -1;
  uint8_t stampSize = 5;
  if (stampText && stampText[0]) {
    stampSize = pickStampFontSize(stampText);
    applyFontSize(stampSize);
    const int stampH = M5.Lcd.fontHeight();
    stampY = kH - kMarginY - stampH;
    contentBottom = stampY - kStampGap;
  }

  st.size = pickMsgFontSize(lines, lineCount, maxW, contentBottom, st.size,
                            st.gap, hasEmoji);

  applyFontSize(st.size);
  M5.Lcd.setTextColor(st.fg, st.bg);

  const int lineH = M5.Lcd.fontHeight();
  int y = msgTopY(st.size, hasEmoji);
  if (hasEmoji)
    emojiDraw(kMarginX, kMarginY, emojiId);

  const int rowH = lineH + st.gap;

  for (uint8_t i = 0; i < lineCount; i++) {
    if (!lines[i] || !lines[i][0])
      continue;
    if (y + lineH > contentBottom)
      break;
    M5.Lcd.drawString(lines[i], textX, y);
    y += rowH;
  }

  if (stampText && stampText[0] && stampY >= 0) {
    applyFontSize(stampSize);
    M5.Lcd.setTextColor(kStampFg, st.bg);
    M5.Lcd.drawString(stampText, kMarginX, stampY);
  }
}
