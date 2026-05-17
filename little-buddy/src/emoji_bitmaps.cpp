#include "emoji_bitmaps.h"
#include <M5Unified.h>
#include <pgmspace.h>
#include <strings.h>

int8_t emojiIdFromName(const char *name) {
  if (!name || !name[0])
    return EMOJI_NONE;
  for (int i = 0; kEmojiTable[i].name; i++) {
    if (strcasecmp(name, kEmojiTable[i].name) == 0)
      return (int8_t)i;
  }
  return EMOJI_NONE;
}

void emojiDraw(int x, int y, int8_t id) {
  if (id < 0 || id >= EMOJI_COUNT)
    return;

  const uint16_t *src = kEmojiTable[id].data;
  static uint16_t lineBuf[EMOJI_W];

  for (int row = 0; row < EMOJI_H; row++) {
    for (int col = 0; col < EMOJI_W; col++)
      lineBuf[col] = pgm_read_word(&src[row * EMOJI_W + col]);
    M5.Lcd.pushImage(x, y + row, EMOJI_W, 1, lineBuf, EMOJI_KEY);
  }
}
