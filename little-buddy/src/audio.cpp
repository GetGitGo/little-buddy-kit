#include "audio.h"
#include <Arduino.h>
#include <M5Unified.h>

static volatile bool s_chimePending = false;

void audioBegin(void) {
  M5.Speaker.begin();
  M5.Speaker.setVolume(96);
}

void audioRequestChime(void) { s_chimePending = true; }

void audioPoll(void) {
  if (!s_chimePending)
    return;
  s_chimePending = false;

  if (!M5.Speaker.isEnabled())
    return;

  constexpr int kCh = 0;
  auto waitMs = [](uint32_t ms) {
    const uint32_t until = millis() + ms;
    while ((int32_t)(until - millis()) > 0) {
      M5.update();
      delay(2);
    }
  };

  M5.Speaker.tone(880.0f, 120, kCh, true);
  waitMs(130);
  M5.Speaker.tone(659.25f, 140, kCh, true);
  waitMs(150);
}
