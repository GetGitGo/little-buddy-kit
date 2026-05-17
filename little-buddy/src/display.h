#pragma once

#include <stdint.h>

struct DisplayStyle {
  uint8_t size; /* 1–6，5–6 为 24 号字放大 */
  uint16_t fg;
  uint16_t bg;
  uint8_t gap; /* 多行额外行距（像素） */
};

void displayBegin(void);
void displayWaiting(void);
uint16_t displayParseColor(const char *s, uint16_t fallback);
void displayLines(const char *const *lines, uint8_t lineCount, const DisplayStyle &style,
                  const char *emojiName = nullptr, const char *stampText = nullptr);
